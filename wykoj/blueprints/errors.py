import logging
import traceback
from typing import Tuple

from quart import Blueprint, Response, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException, Unauthorized

logger = logging.getLogger(__name__)
errors = Blueprint("errors", __name__)


@errors.app_errorhandler(401)  # 401 Unauthorized
async def redirect_to_login(_: Unauthorized) -> Response:
    return redirect(url_for("main.login", next=request.full_path))


@errors.app_errorhandler(HTTPException)
async def http_error_handler(error: HTTPException) -> Tuple[str, int]:
    return await render_template(
        "errors/http_error.html", title=f"{error.code} {error.name}", error=error
    ), error.code


@errors.app_errorhandler(Exception)
async def python_exception_handler(error: Exception) -> Tuple[str, int]:
    logger.error(
        "Python Exception encountered when serving route `%s`\n%s", request.path,
        "".join(traceback.format_exception(type(error), error, error.__traceback__)).rstrip()
    )
    return await render_template(
        "errors/python_exception.html",
        title="Python Exception",
        exception_name=error.__class__.__name__,
        exception_desc=str(error),
        url=request.url
    ), 500
