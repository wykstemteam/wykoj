import asyncio
import logging
from typing import Optional

import ujson as json
from aiohttp import ClientSession, ClientTimeout
from quart import Blueprint, Response, redirect, render_template, request, url_for
from quart_auth import current_user

import wykoj
from wykoj.api.chesscom import ChessComAPI
from wykoj.models import User

logger = logging.getLogger(__name__)
miscellaneous = Blueprint("miscellaneous", __name__)


@miscellaneous.route("/favicon.ico")
async def favicon() -> Response:
    """Favicon redirect: /favicon.ico -> /static/favicon.ico"""
    return redirect(url_for("static", filename="favicon.ico"), 301)


@miscellaneous.route("/chess")
async def chess_page() -> str:
    chesscom_users = await User.exclude(chesscom_username=None)
    # chess.com username to WYKOJ user
    cu_to_user = {user.chesscom_username.lower(): user for user in chesscom_users}

    return await render_template(
        "chess.html",
        title="Chess",
        games=ChessComAPI.recent_games,
        cu_to_user=cu_to_user,
        all_users_retrieved_once=ChessComAPI.all_users_retrieved_once
    )


@miscellaneous.before_app_request
async def clear_trailing_slashes() -> Optional[Response]:
    if request.path != "/" and request.path.endswith("/"):
        return redirect(request.path.rstrip("/"))


@miscellaneous.before_app_request
async def resolve_current_user() -> None:
    """Retrieve current user from database if user is authenticated."""
    await current_user.resolve()


async def update_chess_games() -> None:
    while True:
        async for user in User.exclude(chesscom_username=None):
            await asyncio.sleep(10)
            await ChessComAPI.update_recent_games(user.chesscom_username)
        ChessComAPI.all_users_retrieved_once = True


@miscellaneous.before_app_serving
async def init_session() -> None:
    # ClientSession has to be initiated in async function
    wykoj.session = ClientSession(
        json_serialize=json.dumps,  # ujson
        raise_for_status=True,
        timeout=ClientTimeout(total=10)
    )
    logger.info("aiohttp session created.")
    asyncio.create_task(update_chess_games())


@miscellaneous.after_app_serving
async def close_session() -> None:
    await wykoj.session.close()
    logger.info("aiohttp session closed.")
