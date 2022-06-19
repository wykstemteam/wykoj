import asyncio
import logging
import traceback
from datetime import datetime
from decimal import Decimal

from pytz import utc
from quart import Blueprint, Response, abort, jsonify, request
from tortoise.expressions import F

from wykoj.api import TestCaseAPI
from wykoj.blueprints.utils.access import backend_only
from wykoj.constants import Verdict
from wykoj.models import (
    ContestParticipation, ContestTaskPoints, Submission, Task, TestCaseResult, User
)

judge_api_blueprint = Blueprint("judge", __name__)
logger = logging.getLogger(__name__)


class JudgeSystemError(Exception):
    """Raised when judging a submission fails."""


@judge_api_blueprint.route("/submission/<int:submission_id>/report", methods=["POST"])
@backend_only
async def report_submission_result(submission_id: int) -> Response:
    logger.info(f"[Backend] Report results for submission {submission_id}")

    submission = await Submission.filter(
        id=submission_id
    ).prefetch_related("task", "author", "contest__participations").first()
    if not submission:
        abort(404)

    try:
        config = await TestCaseAPI.get_config(submission.task.task_id)
        data = await request.json

        if "verdict" in data:
            if data["verdict"] in (Verdict.COMPILATION_ERROR, Verdict.SYSTEM_ERROR):
                if data["verdict"] == Verdict.SYSTEM_ERROR:
                    logger.warning(f"[Backend] Reported SE for submission {submission_id}")
                submission.verdict = data["verdict"]
            else:
                logger.error("What are you doing Snuny")
                submission.verdict = Verdict.SYSTEM_ERROR
            await submission.save()
        else:
            test_case_results = [
                TestCaseResult(
                    subtask=tcr["subtask"],
                    test_case=tcr["test_case"],
                    verdict=tcr["verdict"],
                    score=tcr["score"],
                    time_used=tcr["time_used"],
                    memory_used=tcr["memory_used"],
                    submission=submission
                ) for tcr in data["test_case_results"]
            ]

            # Determine overall verdict
            submission.verdict = Verdict.ACCEPTED  # Temporary value
            for test_case_result in test_case_results:
                if (
                    submission.verdict == Verdict.ACCEPTED
                    and test_case_result.verdict != Verdict.ACCEPTED
                    or submission.verdict == Verdict.PARTIAL_SCORE
                    and test_case_result.verdict not in (Verdict.ACCEPTED, Verdict.PARTIAL_SCORE)
                ):
                    submission.verdict = test_case_result.verdict

            # Determine overall score
            if config["batched"]:
                # Lowest score per subtask
                tcr_per_subtask = [[] for _ in range(len(config["points"]))]
                for test_case_result in test_case_results:
                    tcr_per_subtask[test_case_result.subtask - 1].append(test_case_result)

                # Do not use submission.subtask_scores as a list directly
                subtask_scores = []
                for i in range(len(config["points"])):
                    subtask_min_score = min(
                        test_case_result.score for test_case_result in tcr_per_subtask[i]
                    )
                    subtask_scores.append(subtask_min_score * (Decimal(config["points"][i]) / 100))
                submission.subtask_scores = subtask_scores
                submission.score = sum(subtask_scores)
            else:
                # Mean score of all test cases
                submission.score = (
                    sum(tcr.score for tcr in test_case_results) / len(test_case_results)
                )

            if submission.verdict == Verdict.ACCEPTED:
                submission.time_used = max(tcr.time_used for tcr in test_case_results)
                submission.memory_used = max(tcr.memory_used for tcr in test_case_results)

                # Determine if submission is first solve
                submission.first_solve = await Submission.filter(
                    task=submission.task, author=submission.author, first_solve=True
                ).count() == 0
                if submission.first_solve:
                    await asyncio.gather(
                        Task.filter(id=submission.task.id).update(solves=F("solves") + 1),
                        User.filter(id=submission.author.id).update(solves=F("solves") + 1)
                    )

            await submission.save()
            await asyncio.gather(*[tcr.save() for tcr in test_case_results])

            # Prefetch contest-related info
            if submission.contest:
                contest_participation = [
                    cp for cp in submission.contest.participations
                    if cp.contestant_id == submission.author_id
                ][0]
                await contest_participation.fetch_related("task_points")
                await recalculate_contest_task_points(contest_participation, submission.task)
    except Exception as e:
        logger.error(
            f"Error processing submission {submission_id} results:\n" +
            "".join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        )
        logger.error(f"Marked SE for submission {submission_id}")
        submission.verdict = Verdict.SYSTEM_ERROR
        await submission.save()
        return jsonify(success=False)

    judge_duration = (datetime.now(utc) - submission.time).total_seconds()
    logger.info(
        f"Submission {submission_id} {submission.verdict.upper()}, "
        f"{judge_duration:.3f}s after creation"
    )

    return jsonify(success=True)


async def recalculate_contest_task_points(
    contest_participation: ContestParticipation, task: Task
) -> None:
    config = await TestCaseAPI.get_config(task.task_id)
    submissions = await Submission.filter(
        task_id=task.id,
        author_id=contest_participation.contestant_id,
        contest_id=contest_participation.contest_id
    )

    for task_points in contest_participation.task_points:
        if task_points.task_id == task.id:
            break
    else:
        task_points = ContestTaskPoints(task=task, participation=contest_participation)

    if config["batched"]:  # Cumulative subtask score
        task_points.points = [Decimal(0)] * len(config["points"])
        for submission in submissions:
            if not submission.subtask_scores:
                continue

            task_points.points = [
                max(task_points.points[i], submission.subtask_scores[i])
                for i in range(len(config["points"]))
            ]
    else:  # Maximum submission score
        score = 0
        for submission in submissions:
            score = max(score, submission.score)
        task_points.points = [score]

    await task_points.save()
