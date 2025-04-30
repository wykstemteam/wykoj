import asyncio
import logging

from quart import Blueprint, render_template, current_app

from wykoj.api import ChessComAPI
from wykoj.models import User

logger = logging.getLogger(__name__)
chess = Blueprint("chess", __name__, url_prefix="/chess")


@chess.before_app_serving
async def update_chess_games_forever() -> None:
    async def _update_chess_games_forever() -> None:
        while True:
            users = await User.exclude(chesscom_username=None)
            for user in users:
                await asyncio.sleep(20)
                await ChessComAPI.update_recent_games(user.chesscom_username)
            ChessComAPI.all_users_retrieved_once = True

    current_app.add_background_task(_update_chess_games_forever)


@chess.route("/")
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
