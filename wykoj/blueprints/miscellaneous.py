import logging

import ujson as json
from aiohttp import ClientSession, ClientTimeout
from quart import Blueprint, current_app, redirect, url_for, Response
from quart_auth import current_user

import wykoj

logger = logging.getLogger(__name__)
miscellaneous = Blueprint("miscellaneous", __name__)


@miscellaneous.route("/favicon.ico")
async def favicon() -> Response:
    """Favicon redirect: /favicon.ico -> /static/favicon.ico"""
    return redirect(url_for("static", filename="favicon.ico"), 301)


@miscellaneous.before_app_request
async def resolve_current_user() -> None:
    """Retrieve current user from database if user is authenticated."""
    await current_user.resolve()


async def init_session() -> None:  # Before serving
    # ClientSession has to be initiated in async function
    wykoj.session = ClientSession(
        headers={"X-Auth-Token": current_app.secret_key},
        json_serialize=json.dumps,
        raise_for_status=True,
        timeout=ClientTimeout(total=30)
    )
    logger.info("aiohttp session created.")


async def close_session() -> None:  # After serving
    await wykoj.session.close()
    logger.info("aiohttp session closed.")
