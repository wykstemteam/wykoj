import asyncio
import itertools
import logging
from base64 import b64encode, b64decode
from datetime import datetime
from typing import Dict, Any, List, Optional

from tortoise.expressions import F

import wykoj
from wykoj.constants import JUDGE_HOST, ALLOWED_LANGUAGES
from wykoj.models import User, Task, TestCaseResult, Submission, ContestTaskPoints
from wykoj.utils.main import get_running_contest
from wykoj.utils.test_cases import get_config, get_test_cases

logger = logging.getLogger(__name__)


def b64encode_str(s: str) -> str:
    return b64encode(s.encode("utf-8")).decode("utf-8")


def b64decode_str(s: str) -> str:
    return b64decode(s.encode("utf-8")).decode("utf-8")


def append_newline_if_nonexistent(s: str) -> str:
    return s if s.endswith("\n") else s + "\n"


def convert_submission_status(status_id: int) -> int:
    """Convert Judge0 API submission status to WYKOJ submission status"""
    if status_id == 3:
        return 2  # Accepted
    if status_id == 4:
        return 4  # Wrong Answer
    if status_id == 5:
        return 6  # Time Limit Exceeded
    if status_id == 6:
        return 1  # Compilation Error
    if 7 <= status_id <= 12:
        return 5  # Runtime Error
    return 8  # System Error


class JudgeSystemError(Exception):
    """Raised when judging a submission fails."""
    pass


class JudgeAPI:
    """Interface between WYKOJ and self-hosted Judge0 API."""

    @staticmethod
    async def create_and_get_submission(
            source_code: str, language: str, cpu_time_limit: float, memory_limit: int, stdin: str
    ) -> Dict[str, Any]:
        body = {
            "source_code": b64encode_str(source_code),
            "language_id": ALLOWED_LANGUAGES[language],
            "cpu_time_limit": cpu_time_limit,  # s
            "memory_limit": memory_limit * 1024,  # MB -> KB
            "stdin": b64encode_str(stdin)
        }
        async with wykoj.session.post(JUDGE_HOST + "/submissions/", json=body,
                                      params={"base64_encoded": "true", "wait": "true"}) as resp:
            data = await resp.json()
        if isinstance(data, dict) and "error" in data:
            raise JudgeSystemError("error in creating single submission")
        data["stdout"] = data["stdout"] and b64decode_str(data["stdout"])
        data["stderr"] = data["stderr"] and b64decode_str(data["stderr"])
        data["compile_output"] = data["compile_output"] and b64decode_str(data["compile_output"])
        data["message"] = data["message"] and b64decode_str(data["message"])
        if data["message"] == "Internal Error":
            raise JudgeSystemError("internal error in Judge0 API")
        return data

    @staticmethod
    async def create_submission_batch(
            source_code: str, language: str, cpu_time_limit: float, memory_limit: int,
            input_list: List[str], output_list: Optional[List[str]] = None
    ) -> List[str]:
        if output_list and len(input_list) != len(output_list) or len(input_list) == 0:
            raise JudgeSystemError("input/output lists length invalid")
        source_code = b64encode_str(source_code)
        language_id = ALLOWED_LANGUAGES[language]
        stdin = [b64encode_str(i) for i in input_list]
        expected_output = output_list and [b64encode_str(o) for o in output_list]
        body = {"submissions": []}
        for i in range(len(input_list)):
            body["submissions"].append({
                "source_code": source_code,
                "language_id": language_id,
                "cpu_time_limit": float(cpu_time_limit),  # s
                "memory_limit": memory_limit * 1024,  # MB -> KB
                "stdin": stdin[i],
                "expected_output": expected_output[i] if expected_output else None
            })
        async with wykoj.session.post(JUDGE_HOST + "/submissions/batch", json=body,
                                      params={"base64_encoded": "true"}) as resp:
            data = await resp.json()
        if isinstance(data, dict) and "error" in data:
            raise JudgeSystemError("error in getting submission tokens")
        tokens = []
        for submission in data:
            if "token" in submission:
                tokens.append(submission["token"])
            else:
                raise JudgeSystemError("missing submission token")
        return tokens

    @staticmethod
    async def get_submission_batch(tokens: List[str]) -> List[Dict[str, Any]]:
        async with wykoj.session.get(JUDGE_HOST + "/submissions/batch",
                                     params={
                                         "tokens": ",".join(tokens),
                                         "base64_encoded": "true",
                                         "fields": "stdout,message,status_id,time,memory"
                                     }) as resp:
            data = await resp.json()
        if isinstance(data, dict) and "error" in data:
            raise JudgeSystemError("error in submission results")
        data = data["submissions"]
        for submission in data:
            submission["stdout"] = submission["stdout"] and b64decode_str(submission["stdout"])
            submission["message"] = submission["message"] and b64decode_str(submission["message"])
            submission["memory"] = submission["memory"] and submission["memory"] / 1024  # KB -> MB
            if convert_submission_status(submission["status_id"]) == 7 or submission["message"] == "Internal Error":
                raise JudgeSystemError("internal error in Judge0 API")
        return data


async def judge_submission(submission: Submission) -> None:
    start = datetime.now()
    logger.info(f"Judging submission %s...", submission.id)
    config = await get_config(submission.task.task_id)
    test_cases = await get_test_cases(submission.task.task_id)
    if not test_cases:  # This should not happen since they cannot submit but just in case
        logger.error("Test cases not found for task %s.", submission.task_id)
        submission.result = 8  # System Error
        await submission.save()
        return
    try:
        # Try one test case to try for compilation error
        if config["grader"]:
            test_input: str = test_cases[0][0]
        else:
            test_input: str = test_cases[0][0][0]
        result = await JudgeAPI.create_and_get_submission(
            source_code=submission.source_code,
            language=submission.language,
            cpu_time_limit=0.5,
            memory_limit=submission.task.memory_limit,
            stdin=test_input
        )
        if result["status"]["id"] == 6:
            submission.result = 1  # Compilation error
            await submission.save()
            return
        # Judge test cases
        test_cases_combined = itertools.chain(*test_cases)
        if config["grader"]:
            tokens = await JudgeAPI.create_submission_batch(
                source_code=submission.source_code,
                language=submission.language,
                cpu_time_limit=submission.task.time_limit,
                memory_limit=submission.task.memory_limit,
                input_list=list(test_cases_combined)
            )
        else:
            input_list, output_list = zip(*test_cases_combined)
            tokens = await JudgeAPI.create_submission_batch(
                source_code=submission.source_code,
                language=submission.language,
                cpu_time_limit=submission.task.time_limit,
                memory_limit=submission.task.memory_limit,
                input_list=input_list,
                output_list=output_list
            )
        for _ in range(180):  # Wait at most 180 seconds for judging
            await asyncio.sleep(1)
            test_case_results_combined = await JudgeAPI.get_submission_batch(tokens)
            if all(test_case_result["status_id"] > 2 for test_case_result in test_case_results_combined):
                break
        else:
            raise JudgeSystemError("judging timeout")  # Stoopid judge
        # Process judging results
        test_case_results = []
        test_case_results_combined.reverse()  # Reverse for O(1) removal
        to_grade = []
        for i in range(len(test_cases)):  # Create DB objects for test case results
            test_case_results.append([])
            for j in range(len(test_cases[i])):
                test_case_result = TestCaseResult(
                    subtask=i + 1,
                    test_case=j + 1,
                    result=convert_submission_status(test_case_results_combined[-1]["status_id"]),
                    time_used=test_case_results_combined[-1]["time"],
                    memory_used=test_case_results_combined[-1]["memory"],
                    submission=submission
                )
                # Detect TLE and MLE by ourselves since judge may allow them to AC
                if test_case_result.time_used is not None and test_case_result.time_used >= submission.task.time_limit:
                    test_case_result.result = 6  # Time Limit Exceeded
                    test_case_result.time_used = submission.task.time_limit
                    # In case MLE as well
                    test_case_result.memory_used = min(test_case_result.memory_used, submission.task.memory_limit)
                elif (test_case_result.memory_used is not None
                      and test_case_result.memory_used >= submission.task.memory_limit):
                    test_case_result.result = 7  # Memory Limit Exceeded
                    test_case_result.memory_used = submission.task.memory_limit
                if test_case_result.result == 2:
                    test_case_result.score = 100
                    to_grade.append((i, j, test_case_results_combined[-1]["stdout"] or ""))
                del test_case_results_combined[-1]
                test_case_results[-1].append(test_case_result)
        # Grade test case results if necessary
        if config["grader"] and to_grade:
            grading_cases = [
                (append_newline_if_nonexistent(test_cases[i][j]), append_newline_if_nonexistent(test_output))
                for i, j, test_output in to_grade
            ]
            grading_cases = [
                "{} {}\n{}{}".format(test_input.count("\n"), test_output.count("\n"), test_input, test_output)
                for test_input, test_output in grading_cases
            ]
            tokens = await JudgeAPI.create_submission_batch(
                source_code=config["grader_code"],
                language="Python",
                cpu_time_limit=10,
                memory_limit=1024,
                input_list=grading_cases
            )
            for _ in range(180):
                await asyncio.sleep(1)
                grader_results = await JudgeAPI.get_submission_batch(tokens)
                if all(grader_result["status_id"] > 2 for grader_result in grader_results):
                    break
            else:
                raise JudgeSystemError("grading timeout")
            # Process grading results
            for k in range(len(to_grade)):
                if not grader_results[k]["stdout"]:
                    raise JudgeSystemError("grader did not output anything")
                status = grader_results[k]["stdout"].strip().split()
                if not status:
                    raise JudgeSystemError("grader did not output anything")
                i, j, _ = to_grade[k]
                if status[0] == "AC":
                    pass  # No need to modify, originally accepted
                elif status[0] == "PS":
                    test_case_results[i][j].result = 3  # Partial Score
                    test_case_results[i][j].score = float(status[1])
                    if test_case_results[i][j].score == 100:
                        test_case_results[i][j].result = 2  # Accepted
                    elif test_case_results[i][j].score == 0:
                        test_case_results[i][j].result = 4  # Wrong Answer
                elif status[0] == "WA":
                    test_case_results[i][j].result = 4  # Wrong Answer
                    test_case_results[i][j].score = 0
                else:
                    raise JudgeSystemError("grader output invalid status")
        flattened_test_case_results = tuple(itertools.chain(*test_case_results))
        # Determine result
        submission.result = 2  # Accepted (temporary value)
        for test_case_result in flattened_test_case_results:
            if (submission.result == 2 and test_case_result.result != 2
                    or submission.result == 3 and test_case_result.result >= 4):
                submission.result = test_case_result.result
            if submission.result >= 4:
                break
        # Determine score
        if config["batched"]:
            # Lowest score per subtask
            contest = await get_running_contest()
            to_save = []
            is_contest_submission = (contest and contest.status == "ongoing"
                                     and await contest.is_contestant(submission.author))
            if is_contest_submission:
                await contest.fetch_related("participations")
                contest_participation = [
                    cp for cp in contest.participations if cp.contestant_id == submission.author_id
                ][0]
                await contest_participation.fetch_related("task_points")
            for i in range(len(config["points"])):
                submission.score += (min(test_case_result.score for test_case_result in test_case_results[i])
                                     * (config["points"][i] / 100))
                # Handle contest task points
                if is_contest_submission:
                    for task_points in contest_participation.task_points:
                        if task_points.task_id == submission.task_id:
                            break
                    else:  # Make new ContestTaskPoints
                        task_points = ContestTaskPoints(task=submission.task, participation=contest_participation)
                        task_points.points = [0] * len(test_case_results)
                    task_points.points = [
                        max(task_points.points[i],
                            min(test_case_result.score for test_case_result in test_case_results[i])
                            * config["points"][i] / 100)
                        for i in range(len(test_case_results))
                    ]
                    to_save.append(task_points.save())
            if to_save:
                await asyncio.gather(*to_save)
        else:
            # Average score of all test cases
            submission.score = (sum(test_case_result.score for test_case_result in flattened_test_case_results)
                                / len(flattened_test_case_results))
            # Handle contest task points
            contest = await get_running_contest()
            if contest and contest.status == "ongoing" and await contest.is_contestant(submission.author):
                await contest.fetch_related("participations")
                contest_participation = [
                    cp for cp in contest.participations if cp.contestant_id == submission.author_id
                ][0]
                await contest_participation.fetch_related("task_points")
                for task_points in contest_participation.task_points:
                    if task_points.task_id == submission.task_id:
                        break
                else:
                    task_points = ContestTaskPoints(task=submission.task, participation=contest_participation)
                    task_points.points = [0]
                task_points.points = [max(task_points.points[0], submission.score)]
                await task_points.save()
        if submission.result == 2:  # Accepted
            submission.time_used = max(test_case_result.time_used for test_case_result in flattened_test_case_results)
            submission.memory_used = max(test_case_result.memory_used
                                         for test_case_result in flattened_test_case_results)
            # Determine if this submission is first solve
            submission.first_solve = not await Submission.filter(
                task=submission.task, author=submission.author, first_solve=True).count()
            if submission.first_solve:
                await asyncio.gather(
                    Task.filter(id=submission.task.id).update(solves=F("solves") + 1),
                    User.filter(id=submission.author.id).update(solves=F("solves") + 1)
                )
        await submission.save()
        await asyncio.gather(*[test_case_result.save() for test_case_result in flattened_test_case_results])
    except JudgeSystemError as e:
        logger.exception("System Error raised when judging submission %s due to %s (%s).",
                         submission.id, str(e), e.__class__.__name__)
        submission.result = 8  # System Error
        await submission.save()
    except Exception:
        logger.exception("Python Exception raised when judging submission %s.", submission.id)
        submission.result = 8  # System Error
        await submission.save()
    end = datetime.now()
    logger.info(f"Completed judging submission %s in %ss.", submission.id, (end - start).total_seconds())
