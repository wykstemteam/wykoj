import logging

import wykoj
from wykoj.constants import ALLOWED_LANGUAGES, JUDGE_HOST, Verdict
from wykoj.models import Submission

logger = logging.getLogger(__name__)

class JudgeAPI:
    """API between WYKOJ and Judging Backend Server."""

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
