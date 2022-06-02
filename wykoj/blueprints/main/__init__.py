import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Union

from aiocache import cached
from pytz import utc
from quart import Blueprint, Response, abort, flash, redirect, render_template, request, url_for
from quart_auth import current_user, login_required, login_user, logout_user
from tortoise.expressions import Q
from tortoise.functions import Count

from wykoj import __version__, bcrypt
from wykoj.api import TestCaseAPI
from wykoj.blueprints.main.contest import contest_blueprint
from wykoj.blueprints.main.task import task_blueprint
from wykoj.blueprints.main.user import user_blueprint
from wykoj.blueprints.utils.access import contest_redirect
from wykoj.blueprints.utils.misc import (
    get_page, get_recent_solves, get_running_contest, is_safe_url, remove_pfps, save_picture
)
from wykoj.blueprints.utils.pagination import Pagination
from wykoj.constants import ContestStatus, Verdict
from wykoj.forms.main import (
    LoginForm, NonStudentSettingsForm, ResetPasswordForm, StudentSettingsForm
)
from wykoj.models import Contest, Sidebar, Submission, Task, User, UserWrapper
from wykoj.api import NekosBestAPI

logger = logging.getLogger(__name__)

main = Blueprint("main", __name__)
main.register_blueprint(task_blueprint)
main.register_blueprint(user_blueprint)
main.register_blueprint(contest_blueprint)


@main.route("/login", methods=["GET", "POST"])
async def login() -> Union[Response, str]:
    if await current_user.is_authenticated:
        return redirect(url_for("main.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = await User.filter(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(UserWrapper(user.id), remember=True)
            next_page = request.args.get("next")
            return redirect(
                next_page if next_page and is_safe_url(next_page) else url_for("main.home")
            )
        await flash("Login unsuccessful.", "danger")
    return await render_template("login.html", title="Login", form=form)


@main.route("/logout")
async def logout() -> Response:
    logout_user()
    return redirect(url_for("main.home"))


@main.route("/")
@contest_redirect
async def home() -> str:
    current_time = datetime.now(utc)

    sidebar, recent_solves, ongoing_contest, upcoming_contests = await asyncio.gather(
        Sidebar.get(),
        get_recent_solves(),
        get_running_contest(),
        Contest.filter(start_time__gte=current_time).order_by("start_time"),
    )

    if ongoing_contest and ongoing_contest.status == ContestStatus.PREP:
        ongoing_contest = None  # Contests in preparation are upcoming

    return await render_template(
        "home.html",
        title="Home",
        solves=recent_solves,
        ongoing_contest=ongoing_contest,
        upcoming_contests=upcoming_contests,
        current_time=current_time,
        sidebar=sidebar.content
    )


@main.route("/tasks")
@contest_redirect
async def tasks() -> str:
    tasks = await Task.filter(is_public=True)
    if await current_user.is_authenticated:
        solved_tasks = [
            submission.task async for submission in
            Submission.filter(author=current_user.user, first_solve=True).prefetch_related("task")
        ]
    else:
        solved_tasks = []
    await asyncio.gather(*[task.attempts for task in tasks])
    return await render_template(
        "tasks.html", title="Tasks", header="Tasks", tasks=tasks, solved_tasks=solved_tasks
    )


@main.route("/submissions")
@contest_redirect
async def submissions() -> str:
    if current_user.is_admin:
        submissions = Submission.all()
    else:
        submissions = Submission.filter(task__is_public=True)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset(
        (page - 1) * 50
    ).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)
    return await render_template(
        "submissions.html",
        title="Submissions",
        submissions=submissions,
        pagination=pagination,
        show_pagination=cnt > 50
    )


@main.route("/submission/<int:submission_id>")
async def submission_page(submission_id: int) -> str:
    submission = await Submission.filter(
        id=submission_id
    ).prefetch_related("task", "author", "test_case_results", "contest").first()
    if not submission:
        abort(404)

    contest = await get_running_contest()
    if not (
        current_user.is_admin or submission.task.is_public
        and not (contest and await contest.is_contestant(current_user))
        or contest and contest.status == ContestStatus.ONGOING and submission.task in contest.tasks
        and await contest.is_contestant(current_user) and submission.author.id == current_user.id
    ):
        abort(404)

    show_source_code = (
        await current_user.is_authenticated and (
            submission.author.id == current_user.id or current_user.is_admin
            # Solved
            or await current_user.submissions.filter(task=submission.task, first_solve=True).count()
        )
    )

    if (submission.verdict == Verdict.ACCEPTED and current_user.id == submission.author.id
            and current_user.is_admin and current_user.is_student):
        neko_url = await NekosBestAPI.get_url()
    else:
        neko_url = None

    return await render_template(
        "submission.html",
        title=f"Submission {submission.id}",
        submission=submission,
        config=await TestCaseAPI.get_config(submission.task.task_id),
        show_source_code=show_source_code,
        neko_url=neko_url
    )


def add_leaderboard_ranks(users: List[User], solves_attr: str) -> List[Tuple[int, User]]:
    lb = []
    rank = 1
    for i in range(len(users)):
        if i != 0 and getattr(users[i], solves_attr) < getattr(users[i - 1], solves_attr):
            rank = i + 1
        lb.append((rank, users[i]))
    return lb


@cached(ttl=3)
async def get_all_time_leaderboard() -> List[Tuple[int, User]]:
    users = await User.filter(Q(is_student=True) | Q(is_admin=True)).order_by("-solves", "id")
    return add_leaderboard_ranks(users, "solves")


@cached(ttl=3)
async def get_monthly_leaderboard() -> List[Tuple[int, User]]:
    monthly_solves = await Submission.annotate(count=Count("id")).filter(
        time__gte=datetime.now(utc) - timedelta(days=30), first_solve=True
    ).group_by("author_id").order_by("-count").values("author_id", "count")
    monthly_solves = {e["author_id"]: e["count"] for e in monthly_solves}
    users = await User.filter(Q(is_student=True) | Q(is_admin=True), id__in=monthly_solves)
    for user in users:
        user.monthly_solves = monthly_solves[user.id]
    users.sort(key=lambda u: u.monthly_solves, reverse=True)
    return add_leaderboard_ranks(users, "monthly_solves")


@cached(ttl=3)
async def get_weekly_leaderboard() -> List[Tuple[int, User]]:
    weekly_solves = await Submission.annotate(count=Count("id")).filter(
        time__gte=datetime.now(utc) - timedelta(days=7), first_solve=True
    ).group_by("author_id").order_by("-count").values("author_id", "count")
    weekly_solves = {e["author_id"]: e["count"] for e in weekly_solves}
    users = await User.filter(Q(is_student=True) | Q(is_admin=True), id__in=weekly_solves)
    for user in users:
        user.weekly_solves = weekly_solves[user.id]
    users.sort(key=lambda u: u.weekly_solves, reverse=True)
    return add_leaderboard_ranks(users, "weekly_solves")


@main.route("/leaderboard")
@contest_redirect
async def leaderboard() -> str:
    all_time_leaderboard, monthly_leaderboard, weekly_leaderboard = await asyncio.gather(
        get_all_time_leaderboard(),
        get_monthly_leaderboard(),
        get_weekly_leaderboard(),
    )
    return await render_template(
        "leaderboard.html",
        title="Leaderboard",
        all_time_leaderboard=all_time_leaderboard,
        monthly_leaderboard=monthly_leaderboard,
        weekly_leaderboard=weekly_leaderboard
    )


@main.route("/contests")
@contest_redirect
async def contests() -> str:
    contests = Contest.all()
    cnt = await contests.count()
    page = get_page()
    contests = await contests.offset((page - 1) * 50).limit(50)
    pagination = Pagination(contests, page=page, per_page=50, total=cnt)
    contestants = await asyncio.gather(*[contest.get_contestants() for contest in contests])
    return await render_template(
        "contests.html",
        title="Contests",
        contests=zip(contests, [[contestant.id for contestant in c] for c in contestants]),
        pagination=pagination,
        show_pagination=cnt > 50
    )


@main.route("/settings", methods=["GET", "POST"])
@contest_redirect
@login_required
async def settings() -> Union[Response, str]:
    settings_form = StudentSettingsForm() if current_user.is_student else NonStudentSettingsForm()
    reset_password_form = ResetPasswordForm()
    if "profile_pic" in await request.files:
        settings_form.profile_pic.data = (await request.files)["profile_pic"]
    if settings_form.submit.data and await settings_form.full_validate():
        current_user.language = settings_form.language.data
        if not current_user.can_edit_profile:
            current_user.language = settings_form.language.data
            await current_user.save()
            await flash("Settings updated.", "success")
            return redirect(url_for("main.settings"))

        old_fn_40, old_fn_160 = current_user.img_40, current_user.img_160
        fn_40 = fn_160 = None
        if settings_form.profile_pic.data:
            try:
                fn_40, fn_160 = await save_picture(settings_form.profile_pic.data)
            except Exception as e:
                logger.error(f"Error saving profile picture:\n{e.__class__.__name__}: {str(e)}")

        if isinstance(settings_form, NonStudentSettingsForm):
            current_user.username = settings_form.username.data
            current_user.english_name = settings_form.english_name.data

        current_user.name = settings_form.name.data or current_user.username
        current_user.chesscom_username = settings_form.chesscom_username.data
        current_user.img_40 = fn_40 or current_user.img_40
        current_user.img_160 = fn_160 or current_user.img_160
        await current_user.save()

        # Delete old profile pics if they were not the default pics
        if fn_40 and old_fn_40 != "default_40.png":
            await remove_pfps(old_fn_40, old_fn_160)

        await flash("Settings updated.", "success")
        return redirect(url_for("main.settings"))
    elif reset_password_form.save.data and reset_password_form.validate_on_submit():
        if bcrypt.check_password_hash(
            current_user.password, reset_password_form.current_password.data
        ):
            # Allows old pw = new pw, anyway
            current_user.password = bcrypt.generate_password_hash(
                reset_password_form.new_password.data
            ).decode("utf-8")
            await current_user.save()
            await flash("Password updated.", "success")
        else:
            await flash("Incorrect password.", "danger")
        return redirect(url_for("main.settings"))
    elif request.method == "GET":
        settings_form.name.data = current_user.name
        settings_form.chesscom_username.data = current_user.chesscom_username
        settings_form.language.data = current_user.language
        if isinstance(settings_form, NonStudentSettingsForm):
            settings_form.username.data = current_user.username
            settings_form.english_name.data = current_user.english_name
        if not current_user.can_edit_profile:
            await flash("You are restricted from editing your profile.", "danger")

    return await render_template(
        "settings.html",
        title="Settings",
        settings_form=settings_form,
        reset_password_form=reset_password_form
    )


@main.route("/info")
@contest_redirect
async def info() -> str:
    return await render_template("info.html", title="Info", version=__version__)


@main.route("/buyAccount")
async def buy_account() -> str:
    return await render_template("buy_account.html", title="Buy Account")
