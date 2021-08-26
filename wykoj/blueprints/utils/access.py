import logging
from functools import wraps
from typing import Any, Callable

from quart import abort, current_app, redirect, request, url_for
from quart_auth import current_user, login_required
from quart_rate_limiter import rate_exempt

from wykoj.blueprints.utils.misc import get_running_contest

logger = logging.getLogger(__name__)


def contest_redirect(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to redirect contestants to contest page if they try to access an unrelated page."""
    @wraps(f)
    async def inner(*args: Any, **kwargs: Any) -> Any:
        contest = await get_running_contest()
        if (
            contest and await current_user.is_authenticated and not current_user.is_admin
            and await contest.is_contestant(current_user)
        ):
            return redirect(url_for("main.contest.contest_page", contest_id=contest.id))
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


def backend_only(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to restrict route access to judging backend."""
    @rate_exempt
    @wraps(f)
    async def inner(*args: Any, **kwargs: Any) -> Any:
        if request.headers.get("X-Auth-Token") != current_app.secret_key:
            logger.warn(f"Unauthorized access to endpoint {request.full_path}")
            abort(403)
        return await f(*args, **kwargs)

    return inner
