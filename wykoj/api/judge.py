import logging

from aiohttp import ClientTimeout
from quart import current_app

import wykoj
from wykoj.api.test_cases import TestCaseAPI
from wykoj.constants import ALLOWED_LANGUAGES, Verdict
from wykoj.models import Submission

logger = logging.getLogger(__name__)


class JudgeAPI:
    """Wrapper for WYKOJ Judge Server API."""
    _is_online = False

    @staticmethod
    def is_online() -> bool:
        return JudgeAPI._is_online

    @staticmethod
    async def update_status() -> None:
        try:
            await wykoj.session.get(
                current_app.config["JUDGE_HOST"] + "/ping", timeout=ClientTimeout(total=5)
            )
        except Exception as e:
            logger.error(f"Error in checking Judge API status:\n{e.__class__.__name__}: {str(e)}")
            JudgeAPI._is_online = False
        else:
            JudgeAPI._is_online = True

    @staticmethod
    async def pull_test_cases() -> None:
        try:
            await wykoj.session.post(
                current_app.config["JUDGE_HOST"] + "/pull_test_cases",
                headers={"X-Auth-Token": current_app.secret_key}
            )
        except Exception as e:
            logger.error(
                f"Error in sending pull test cases request:\n{e.__class__.__name__}: {str(e)}"
            )

    @staticmethod
    async def judge_submission(submission: Submission) -> None:
        await submission.fetch_related("task")
        task = submission.task
        config = await TestCaseAPI.get_config(task.task_id)

        task_info = {
            "task_id": task.task_id,
            "time_limit": float(task.time_limit),
            "memory_limit": task.memory_limit,
            "grader": config["grader"]
        }
        if config["grader"]:
            task_info["grader_source_code"] = config["grader_source_code"]
            task_info["grader_language"] = ALLOWED_LANGUAGES[config["grader_language"]]

        body = {
            "task_info": task_info,
            "submission": {
                "id": submission.id,
                "language": ALLOWED_LANGUAGES[submission.language],
                "source_code": submission.source_code
            }
        }

        try:
            await wykoj.session.post(
                current_app.config["JUDGE_HOST"] + "/judge",
                json=body,
                headers={"X-Auth-Token": current_app.secret_key}
            )
        except Exception as e:
            logger.error(
                f"Error in sending judge submission request:\n{e.__class__.__name__}: {str(e)}"
            )
            logger.error(f"Marked SE for submission {submission.id}")
            submission.verdict = Verdict.SYSTEM_ERROR
            await submission.save()
            raise e from None
