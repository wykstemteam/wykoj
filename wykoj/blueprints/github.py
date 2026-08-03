import hashlib
import hmac
import logging
import os
import subprocess

from quart import Blueprint, abort, current_app, jsonify, request

from wykoj.api import JudgeAPI

logger = logging.getLogger(__name__)
github = Blueprint("github", __name__, url_prefix="/github")


def update_test_cases() -> None:
    env = os.environ.copy()
    github_token = current_app.config.get('GITHUB_TOKEN')
    if github_token:
        # Authenticates git's https://github.com/... requests with this
        # token, scoped only to this subprocess call (never written to
        # disk, e.g. no ~/.git-credentials or .git/config change).
        env['GIT_CONFIG_COUNT'] = '1'
        env['GIT_CONFIG_KEY_0'] = f'url.https://{github_token}@github.com/.insteadOf'
        env['GIT_CONFIG_VALUE_0'] = 'https://github.com/'

    proc = subprocess.run(
        ['git', 'submodule', 'foreach', 'git', 'pull', 'origin', 'master'],
        capture_output=True,
        env=env
    )
    output = proc.stdout.decode() + proc.stderr.decode()
    if proc.returncode != 0:
        logger.error(f"[GitHub] Failed to update test cases\n{output}")
    else:
        logger.info(f"[GitHub] Updated test cases\n{output}")


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
