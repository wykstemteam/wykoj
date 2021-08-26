import asyncio
import logging
import os.path
from secrets import token_hex
from typing import List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse

import aiofiles.os
from aiocache import cached
from PIL import Image
from quart import abort, current_app, request, url_for
from quart.datastructures import FileStorage
from quart.utils import run_sync
from tortoise.fields import ManyToManyRelation

from wykoj.constants import ContestStatus, Verdict
from wykoj.models import Contest, Submission, User

logger = logging.getLogger(__name__)


async def get_running_contest() -> Optional[Contest]:
    async for contest in Contest.all().prefetch_related("tasks"):
        if contest.status in (ContestStatus.PREP, ContestStatus.ONGOING):
            return contest
    return None


@cached(ttl=3)
async def get_recent_solves() -> List[Submission]:
    return await Submission.filter(first_solve=True, task__is_public=True).limit(8)


@cached(ttl=3)
async def get_epic_fails() -> List[Submission]:
    return await Submission.filter(
        verdict__in=(
            Verdict.COMPILATION_ERROR, Verdict.WRONG_ANSWER, Verdict.RUNTIME_ERROR,
            Verdict.TIME_LIMIT_EXCEEDED, Verdict.MEMORY_LIMIT_EXCEEDED
        ),
        task__is_public=True
    ).limit(5)


def join_authors(authors: Union[List[User], ManyToManyRelation[User]]) -> str:
    if not authors:
        return ""
    usernames = [
        f'<a href="{url_for("main.user.user_page", username=a.username)}">{a.username}</a>'
        for a in authors if a
    ]
    if len(usernames) == 1:
        return usernames[0]
    return ", ".join(usernames[:-1]) + " and " + usernames[-1]


def join_contests(contests: Union[List[Contest], ManyToManyRelation[Contest]]) -> str:
    if not contests:
        return ""
    contests = [
        f'<a href="{url_for("main.contest.contest_page", contest_id=c.id)}">{c.title}</a>' for c in contests
        if c
    ]
    if len(contests) == 1:
        return contests[0]
    return ", ".join(contests[:-1]) + " and " + contests[-1]


def is_safe_url(target: str) -> bool:
    """Check if url is safe for redirection."""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def get_page() -> int:
    """Get the url parameter "page" on pages supporting pagination."""
    try:
        page = request.args.get("page", 1, type=int)
        if page < 1:
            raise ValueError
        return page
    except ValueError:
        abort(400)


async def save_picture(profile_pic: FileStorage) -> Tuple[str, str]:
    """Save user profile picture locally inside static/profile_pics/."""
    filename = token_hex(8)
    _, ext = os.path.splitext(profile_pic.filename)
    if ext == ".jpeg":
        ext = ".jpg"
    fn_40 = filename + "_40" + ext
    fn_160 = filename + "_160" + ext

    def _save_picture() -> None:
        im = Image.open(profile_pic)
        im = im.convert("RGB")
        im_40 = im.resize((40, 40))
        im_40.save(os.path.join(current_app.root_path, "static", "profile_pics", fn_40), quality=95)
        im_160 = im.resize((160, 160))
        im_160.save(
            os.path.join(current_app.root_path, "static", "profile_pics", fn_160), quality=95
        )

    await run_sync(_save_picture)()
    return fn_40, fn_160


async def remove_pfps(old_fn_40: str, old_fn_160: str) -> None:
    await asyncio.gather(
        aiofiles.os.remove(
            os.path.join(current_app.root_path, "static", "profile_pics", old_fn_40)
        ),
        aiofiles.os.remove(
            os.path.join(current_app.root_path, "static", "profile_pics", old_fn_160)
        )
    )
