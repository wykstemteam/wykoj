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
    # .git (and the submodule's gitdir under .git/modules/) is bind-mounted
    # from the host in Docker, so it's owned by the host user rather than
    # whichever user runs this container process. Git refuses to operate on
    # repos it doesn't own by default (CVE-2022-24765); this opts back in,
    # scoped to this subprocess call only.
    config_entries = [("safe.directory", "*")]

    github_token = current_app.config.get('GITHUB_TOKEN')
    if github_token:
        # Authenticates git's https://github.com/... requests with this
        # token, scoped only to this subprocess call (never written to
        # disk, e.g. no ~/.git-credentials or .git/config change).
        config_entries.append((f'url.https://{github_token}@github.com/.insteadOf', 'https://github.com/'))

    env['GIT_CONFIG_COUNT'] = str(len(config_entries))
    for i, (key, value) in enumerate(config_entries):
        env[f'GIT_CONFIG_KEY_{i}'] = key
        env[f'GIT_CONFIG_VALUE_{i}'] = value

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
