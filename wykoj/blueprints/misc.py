import asyncio
import logging
from typing import Optional

import ujson as json
from aiohttp import ClientConnectorError, ClientTimeout, ServerDisconnectedError
from aiohttp_retry import ExponentialRetry, RetryClient
from quart import Blueprint, Response, redirect, request, url_for, current_app
from quart_auth import current_user

import wykoj
from wykoj.api import JudgeAPI

logger = logging.getLogger(__name__)
misc = Blueprint("misc", __name__)


@misc.route("/favicon.ico")
async def favicon() -> Response:
    """Favicon redirect: /favicon.ico -> /static/favicon.ico"""
    return redirect(url_for("static", filename="favicon.ico"), 301)


@misc.before_app_request
async def clear_trailing_slashes() -> Optional[Response]:
    if request.path != "/" and request.path.endswith("/"):
        return redirect(request.path.rstrip("/"))


@misc.before_app_request
async def resolve_current_user() -> None:
    """Retrieve current user from database if user is authenticated."""
    await current_user.resolve()


@misc.before_app_serving
async def init_session() -> None:
    # ClientSession has to be initiated in async function
    retry_options = ExponentialRetry(
        attempts=3, exceptions=[TimeoutError, ClientConnectorError, ServerDisconnectedError]
    )
    current_app.session = RetryClient(
        json_serialize=json.dumps,  # ujson
        raise_for_status=True,
        timeout=ClientTimeout(total=5),
        retry_options=retry_options
    )


@misc.after_app_serving
async def close_session() -> None:
    await current_app.session.close()


@misc.before_app_serving
async def check_judge_status_forever() -> None:
    async def _check_judge_status_forever() -> None:
        while True:
            await JudgeAPI.update_status()
            await asyncio.sleep(60)

    current_app.add_background_task(_check_judge_status_forever)
