import asyncio
import logging
import traceback
from collections import Counter
from datetime import datetime
from decimal import Decimal

from pytz import utc
from quart import Blueprint, Response, abort, current_app, jsonify, request
from quart_auth import current_user
from tortoise.expressions import F
from tortoise.query_utils import Q

from wykoj.constants import ContestStatus, Verdict
from wykoj.models import ContestTaskPoints, Submission, Task, TestCaseResult, User
from wykoj.utils.main import get_running_contest
from wykoj.utils.test_cases import get_config, get_test_cases

logger = logging.getLogger(__name__)
api = Blueprint("api", __name__)


@api.route("/search")
async def search() -> Response:
    """JSON API endpoint for search results."""
    query: str = request.args.get("query", "").strip()
    if len(query) < 3 or len(query) > 50:
        return jsonify(users=[], tasks=[])
    task_query = Q(task_id__icontains=query) | Q(title__icontains=query)
    if not current_user.is_admin:
        task_query &= Q(is_public=True)
    tasks = await Task.filter(task_query).only("task_id", "title")
    tasks = [{"task_id": task.task_id, "title": task.title} for task in tasks]
    user_query = Q(username__icontains=query) | Q(name__icontains=query)
    if await current_user.is_authenticated:
        user_query |= Q(english_name__icontains=query)
    users = await User.filter(user_query).only("username", "name")
    users = [{"username": user.username, "name": user.name} for user in users]
    return jsonify(tasks=tasks, users=users)


@api.route("/user/<string:username>/submission_languages")
async def user_submission_languages(username: str) -> Response:
    """JSON API endpoint for distribution of languages used in user submissions."""
    # Not much point in excluding submissions to non-public tasks
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)
    submissions = await user.submissions.all().only("language")
    languages = Counter([submission.language for submission in submissions])
    if len(languages) > 10:
        data = languages.most_common(9)
        data.append(("Other", sum(languages.values()) - sum(dict(data).values())))
    else:
        data = languages.most_common()
    languages, occurrences = list(zip(*data))
    return jsonify(languages=languages, occurrences=occurrences)


@api.route("/task/<string:task_id>/info")
async def task_info(task_id) -> Response:
    if request.headers.get("X-Auth-Token") != current_app.secret_key:
        logger.warn(f"Unauthorized task info request for {task_id}")
        abort(403)

    logger.info(f"Task info requested for {task_id}")

    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)

    config, test_cases = await asyncio.gather(
        get_config(task.task_id), get_test_cases(task.task_id)
    )

    test_case_objects = []
    for subtask in range(len(test_cases)):
        for test_case in range(len(test_cases[subtask])):
            test_case_objects.append(
                {
                    "subtask": subtask + 1,
                    "test_case": test_case + 1,
                    "input": test_cases[subtask][test_case][0],
                    "output": test_cases[subtask][test_case][1]
                }
            )

    return jsonify(
        time_limit=float(task.time_limit),
        memory_limit=task.memory_limit,
        grader=config["grader"],
        test_cases=test_case_objects
    )


class JudgeSystemError(Exception):
    """Raised when judging a submission fails."""
    pass


@api.route("/submission/<int:submission_id>/report", methods=["POST"])
async def report_submission_result(submission_id: int) -> Response:
    if request.headers.get("X-Auth-Token") != current_app.secret_key:
        logger.warn(f"Unauthorized results reported for submission {submission_id}")
        abort(403)

    logger.info(f"Results reported for submission {submission_id}")

    submission = await Submission.filter(id=submission_id).prefetch_related("task",
                                                                            "author").first()
    if not submission:
        abort(404)

    try:
        config = await get_config(submission.task.task_id)
        data = await request.json

        if "verdict" in data:
            if data["verdict"] in (Verdict.COMPILATION_ERROR, Verdict.SYSTEM_ERROR):
                submission.verdict = data["verdict"]
            else:
                logging.error("What are you doing Snuny")
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

            # Prefetch contest-related info
            contest = await get_running_contest()
            is_contest_submission = (
                contest and contest.status == ContestStatus.ONGOING
                and await contest.is_contestant(submission.author)
            )
            if is_contest_submission:
                await contest.fetch_related("participations")
                contest_participation = [
                    cp for cp in contest.participations if cp.contestant_id == submission.author_id
                ][0]
                await contest_participation.fetch_related("task_points")

            # Determine overall score
            if config["batched"]:
                # Lowest score per subtask
                tcr_per_subtask = [[] for _ in range(len(config["points"]))]
                for test_case_result in test_case_results:
                    tcr_per_subtask[test_case_result.subtask - 1].append(test_case_result)

                subtask_scores = []
                for i in range(len(config["points"])):
                    subtask_min_score = min(
                        test_case_result.score for test_case_result in tcr_per_subtask[i]
                    )
                    subtask_scores.append(subtask_min_score * (Decimal(config["points"][i]) / 100))
                submission.score = sum(subtask_scores)

                # Handle contest task points
                if is_contest_submission:
                    for task_points in contest_participation.task_points:
                        if task_points.task_id == submission.task_id:
                            break
                    else:  # Make new ContestTaskPoints
                        task_points = ContestTaskPoints(
                            task=submission.task, participation=contest_participation
                        )
                        task_points.points = [Decimal(0)] * len(config["points"])

                    task_points.points = [
                        max(task_points.points[i], subtask_scores[i])
                        for i in range(len(config["points"]))
                    ]
                    await task_points.save()
            else:
                # Mean score of all test cases
                submission.score = (
                    sum(tcr.score for tcr in test_case_results) / len(test_case_results)
                )

                # Handle contest task points
                if is_contest_submission:
                    for task_points in contest_participation.task_points:
                        if task_points.task_id == submission.task_id:
                            break
                    else:
                        task_points = ContestTaskPoints(
                            task=submission.task, participation=contest_participation
                        )
                        task_points.points = [0]

                    task_points.points = [max(task_points.points[0], submission.score)]
                    await task_points.save()

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
    except Exception as e:
        logger.error(
            f"Error in judging submission:\n" +
            "".join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        )
        submission.verdict = Verdict.SYSTEM_ERROR
        await submission.save()
        return jsonify(success=False)

    judge_duration = (datetime.now(utc) - submission.time).total_seconds()
    logger.info(f"Submission {submission_id} finished judging {judge_duration:.3f}s after creation")
    return jsonify(success=True)
