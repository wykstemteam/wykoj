import html
import os
from functools import wraps
from secrets import token_hex
from typing import Any, Awaitable, Callable, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse

from aiocache import cached
from flask_wtf import FlaskForm
from PIL import Image
from quart import abort, current_app, flash, redirect, request, url_for
from quart.datastructures import FileStorage
from quart.utils import run_sync
from quart_auth import current_user, login_required
from tortoise.fields import ManyToManyRelation
from wtforms import Field
from wtforms.validators import ValidationError

from wykoj.constants import ContestStatus, Verdict
from wykoj.models import Contest, Submission, User


def contest_redirect(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to redirect contestants to contest page if they try to access an unrelated page."""
    @wraps(f)
    async def inner(*args: Any, **kwargs: Any) -> Any:
        contest = await get_running_contest()
        if (
            contest and await current_user.is_authenticated and not current_user.is_admin
            and await contest.is_contestant(current_user)
        ):
            return redirect(url_for("main.contest_page", contest_id=contest.id))
        return await f(*args, **kwargs)

    return inner


def admin_only(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to restrict route access to admins."""
    @login_required
    @wraps(f)
    async def inner(*args: Any, **kwargs: Any) -> Any:
        if not current_user.is_admin:
            abort(403)
        return await f(*args, **kwargs)

    return inner


def editor_widget(field: Field, **kwargs: Any) -> str:
    """A code editor for forms including code."""
    # The code editor creates its own textarea which is not treated as form data
    # So we create a hidden textarea and listen for changes in the editor
    # (This took way too long to implement)
    kwargs.setdefault("id", field.id)
    if "value" not in kwargs:
        kwargs["value"] = field._value()
    return (
        f'<textarea id="{field.id}" name="{field.id}" type="text"'
        'maxlength="1000000" style="display: none;"></textarea>\n'
        f'<div id="editor" class="{kwargs.get("class", "")}">{html.escape(field.data or "")}</div>'
    )


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
        f'<a href="{url_for("main.user_page", username=a.username)}">{a.username}</a>'
        for a in authors if a
    ]
    if len(usernames) == 1:
        return usernames[0]
    return ", ".join(usernames[:-1]) + " and " + usernames[-1]


def join_contests(contests: Union[List[Contest], ManyToManyRelation[Contest]]) -> str:
    if not contests:
        return ""
    contests = [
        f'<a href="{url_for("main.contest_page", contest_id=c.id)}">{c.title}</a>' for c in contests
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


async def validate(form: FlaskForm) -> bool:
    """Since WTForms does not accept async validators,
    this function helps validate both sync and custom async validators.
    A danger message is flashed if an async validator fails.
    """
    if not form.validate_on_submit():
        return False  # Handles the case where form is not submitted
    try:
        await form.async_validate()
    except ValidationError as e:
        await flash(str(e), "danger")
        return False
    except AttributeError:
        pass
    return True


async def save_picture(profile_pic: FileStorage) -> Tuple[str, str]:
    """Save user profile picture locally inside static/profile_pics/."""
    name = token_hex(8)
    _, ext = os.path.splitext(profile_pic.filename)
    if ext == ".jpeg":
        ext = ".jpg"
    fn_40 = name + "_40" + ext
    fn_160 = name + "_160" + ext

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
    def _remove_pfps() -> None:
        os.remove(os.path.join(current_app.root_path, "static", "profile_pics", old_fn_40))
        os.remove(os.path.join(current_app.root_path, "static", "profile_pics", old_fn_160))

    await run_sync(_remove_pfps)()
