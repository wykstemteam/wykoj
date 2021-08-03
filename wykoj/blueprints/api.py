import asyncio
import hashlib
import logging
import traceback
from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator

import ujson as json
from aiocache import cached
from pytz import utc
from quart import Blueprint, Response, abort, current_app, jsonify, request
from quart.wrappers.response import IterableBody
from quart_auth import current_user
from tortoise.expressions import F
from tortoise.query_utils import Q

from wykoj.constants import ContestStatus, Verdict
from wykoj.models import (
    ContestParticipation, ContestTaskPoints, Submission, Task, TestCaseResult, User
)
from wykoj.utils.main import backend_only, get_running_contest
from wykoj.utils.test_cases import get_config, iter_test_cases

logger = logging.getLogger(__name__)
api = Blueprint("api", __name__)

# Client-side API


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


# Backend API


# Stream response becuase the judge breaks when the response is large (>100 MB)
# It just shuts down after showing the message "Killed"
async def generate_response(task: Task) -> AsyncIterator[str]:
    config = await get_config(task.task_id)

    metadata = {
        "time_limit": float(task.time_limit),
        "memory_limit": task.memory_limit,
        "grader": config["grader"]
    }
    yield '{"metadata":' + json.dumps(metadata) + ',"test_cases":['

    first = True  # Do not add comma before first test case
    async for test_case in iter_test_cases(task.task_id):
        if first:
            yield test_case.json()
            first = False
        else:
            yield "," + test_case.json()

    yield "]}"


@api.route("/task/<string:task_id>/info")
@backend_only
async def task_info(task_id: str) -> Response:
    logger.info(f"Task info requested for {task_id}")

    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)

    return Response(IterableBody(generate_response(task)), mimetype="application/json")


@cached(ttl=10)
async def get_task_info_checksum(task: Task) -> str:
    checksum = hashlib.sha384()
    async for chunk in generate_response(task):
        checksum.update(chunk.encode())
    return checksum.hexdigest()


@api.route("/task/<string:task_id>/info/checksum")
@backend_only
async def task_info_checksum(task_id: str) -> Response:
    logger.info(f"Task info checksum requested for {task_id}")

    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)

    checksum = await get_task_info_checksum(task)
    return jsonify(checksum=checksum)


class JudgeSystemError(Exception):
    """Raised when judging a submission fails."""
    pass


@api.route("/submission/<int:submission_id>/report", methods=["POST"])
@backend_only
async def report_submission_result(submission_id: int) -> Response:
    logger.info(f"Results reported for submission {submission_id}")

    submission = await Submission.filter(
        id=submission_id
    ).prefetch_related("task", "author", "contest__participations").first()
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
            is_contest_submission = submission.contest and await submission.contest.is_contestant(
                submission.author
            )
            if is_contest_submission:
                contest_participation = [
                    cp for cp in submission.contest.participations
                    if cp.contestant_id == submission.author_id
                ][0]
                await contest_participation.fetch_related("task_points")
                await recalculate_contest_task_points(contest_participation, submission.task)
    except Exception as e:
        logger.error(
            f"Error in judging submission:\n" +
            "".join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        )
        submission.verdict = Verdict.SYSTEM_ERROR
        await submission.save()
        return jsonify(success=False)

    # Possibly at most 1 second off because microsecond is stripped from submission time
    judge_duration = (datetime.now(utc) - submission.time).total_seconds()
    logger.info(f"Submission {submission_id} finished judging {judge_duration:.3f}s after creation")

    return jsonify(success=True)


async def recalculate_contest_task_points(
    contest_participation: ContestParticipation, task: Task
) -> None:
    config = await get_config(task.task_id)
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
