import logging

from aiocache import cached
from aiohttp import ClientTimeout, ClientConnectorError

import wykoj
from wykoj.constants import ALLOWED_LANGUAGES, JUDGE_HOST, SECRET_KEY, Verdict
from wykoj.models import Submission

logger = logging.getLogger(__name__)

class JudgeAPI:
    """Wrapper for WYKOJ Judge Server API."""

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
            await wykoj.session.post(
                JUDGE_HOST + "/judge", json=body, params=params, headers={"X-Auth-Token": SECRET_KEY}
            )
        except Exception as e:
            logger.error(f"Error in judging submission:\n{type(e)}: {str(e)}")
            submission.verdict = Verdict.SYSTEM_ERROR
            await submission.save()
            raise e
