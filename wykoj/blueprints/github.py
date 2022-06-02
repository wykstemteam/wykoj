import asyncio
import logging

from quart import Blueprint, abort, current_app, jsonify, request

logger = logging.getLogger(__name__)
github = Blueprint("github", __name__, url_prefix="/github")


async def update_test_cases() -> None:
    logger.info("[GitHub] Updating test cases")

    # https://docs.python.org/3/library/asyncio-subprocess.html
    proc = await asyncio.create_subprocess_shell(
        "git submodule update",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if stdout:
        logger.info(stdout.decode())
    if stderr:
        logger.error(stderr.decode())


@github.before_app_serving
async def before_serving() -> None:
    current_app.add_background_task(update_test_cases)


@github.route("/push")
async def push() -> str:
    # Check secret key
    if request.headers.get("X-Hub-Signature") != current_app.secret_key:
        logger.warn(f"Unauthorized access to endpoint {request.full_path}")
        abort(403)

    current_app.add_background_task(update_test_cases)
    return jsonify(success=True)
