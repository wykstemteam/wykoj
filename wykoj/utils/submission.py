import logging

from aiocache import cached

import wykoj
from wykoj.constants import ALLOWED_LANGUAGES, JUDGE_HOST, Verdict
from wykoj.models import Submission
from aiohttp import ClientTimeout, ClientConnectorError

logger = logging.getLogger(__name__)

class JudgeAPI:
    """API between WYKOJ and Judge Server."""

    @staticmethod
    @cached(ttl=5)
    async def is_online() -> bool:
        try:
            await wykoj.session.get(JUDGE_HOST + "/", timeout=ClientTimeout(total=0.5))
        except ClientConnectorError:
            return False
        except Exception as e:
            logger.error(f"Error in checking if judge server is up:\n{type(e)}: {str(e)}")
            return False
        else:
            return True

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
            await wykoj.session.post(JUDGE_HOST + "/judge", json=body, params=params)
        except Exception as e:
            logger.error(f"Error in judging submission:\n{type(e)}: {str(e)}")
            submission.verdict = Verdict.SYSTEM_ERROR
            await submission.save()
            raise e
