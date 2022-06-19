import asyncio
import hashlib
import hmac
import logging

from quart import Blueprint, abort, current_app, jsonify, request

from wykoj.api import JudgeAPI

logger = logging.getLogger(__name__)
github = Blueprint("github", __name__, url_prefix="/github")


async def update_test_cases() -> None:
    # https://docs.python.org/3/library/asyncio-subprocess.html
    proc = await asyncio.create_subprocess_shell(
        "git submodule foreach git pull origin master",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    logger.info("[GitHub] Updated test cases\n" + stdout.decode() + stderr.decode())


@github.before_app_serving
async def before_serving() -> None:
    current_app.add_background_task(update_test_cases)


@github.route("/push", methods=["POST"])
async def push() -> str:
    checksum = hmac.new(current_app.secret_key.encode(), await request.data, hashlib.sha256)

    if request.headers.get("X-Hub-Signature-256") != f"sha256={checksum.hexdigest()}":
        logger.warn(f"Unauthorized access to endpoint {request.full_path}")
        abort(403)

    logger.info("[GitHub] Push update received")
    current_app.add_background_task(update_test_cases)
    current_app.add_background_task(JudgeAPI.pull_test_cases)
    return jsonify(success=True)
