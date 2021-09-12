import logging
from typing import Optional

import ujson as json
from aiohttp import ClientSession, ClientTimeout
from quart import Blueprint, Response, redirect, request, url_for
from quart_auth import current_user

import wykoj

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
    wykoj.session = ClientSession(
        json_serialize=json.dumps,  # ujson
        raise_for_status=True,
        timeout=ClientTimeout(total=30)
    )
    logger.info("aiohttp session created.")


@misc.after_app_serving
async def close_session() -> None:
    await wykoj.session.close()
    logger.info("aiohttp session closed.")
