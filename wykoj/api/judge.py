import logging

from aiohttp import ClientTimeout
from quart import current_app

import wykoj
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
                current_app.config["JUDGE_HOST"] + "/ping", timeout=ClientTimeout(total=3)
            )
        except Exception as e:
            logger.error(
                f"Error in checking Judge API status:\n{e.__class__.__name__}: {str(e)}"
            )
            JudgeAPI._is_online = False
        else:
            JudgeAPI._is_online = True

    @staticmethod
    async def judge_submission(submission: Submission) -> None:
        logger.info(f"Sending request to judge submission {submission.id}")
        params = {
            "submission_id": submission.id,
            "task_id": submission.task.task_id,
            "language": ALLOWED_LANGUAGES[submission.language]
        }
        body = {"source_code": submission.source_code}
        try:
            await wykoj.session.post(
                current_app.config["JUDGE_HOST"] + "/judge",
                json=body,
                params=params,
                headers={"X-Auth-Token": current_app.secret_key}
            )
        except Exception as e:
            logger.error(f"Error in sending judge submission request:\n{e.__class__.__name__}: {str(e)}")
            logger.error(f"Marked SE for submission {submission.id}")
            submission.verdict = Verdict.SYSTEM_ERROR
            await submission.save()
            raise e from None
