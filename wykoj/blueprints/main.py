import asyncio
import re
from datetime import datetime, timedelta
from statistics import mean, median, pstdev
from typing import Union, Optional, List, Tuple

from aiocache import cached
from pytz import utc
from quart import Blueprint, render_template, url_for, flash, redirect, request, abort, Response
from quart_auth import login_user, logout_user, current_user, login_required
from tortoise.query_utils import Q

from wykoj import __version__, bcrypt
from wykoj.forms.main import (
    TaskSubmitForm, LoginForm, StudentSettingsForm, NonStudentSettingsForm, ResetPasswordForm
)
from wykoj.models import (
    Sidebar, User, UserWrapper, Task, Submission,
    ContestParticipation, Contest, Submission
)
from wykoj.utils.main import (
    contest_redirect, get_running_contest, get_recent_solves, get_epic_fails, join_authors,
    join_contests, is_safe_url, get_page, validate, save_picture, remove_pfps
)
from wykoj.utils.pagination import Pagination
from wykoj.utils.submission import JudgeAPI
from wykoj.utils.test_cases import get_config, get_sample_test_cases, get_test_cases

main = Blueprint("main", __name__)


@main.route("/")
@contest_redirect
async def home() -> str:
    current_time = datetime.now(utc)

    sidebar, recent_solves, epic_fails, ongoing_contest, upcoming_contests = await asyncio.gather(
        Sidebar.get(),
        get_recent_solves(),
        get_epic_fails(),
        get_running_contest(),
        Contest.filter(start_time__gte=current_time).order_by("start_time")
    )

    if ongoing_contest and ongoing_contest.status == "prep":
        ongoing_contest = None  # Contests in preparation are upcoming

    return await render_template(
        "home.html", title="Home", solves=recent_solves, epic_fails=epic_fails,
        ongoing_contest=ongoing_contest, upcoming_contests=upcoming_contests,
        current_time=current_time, sidebar=sidebar.content, int=int
    )


@main.route("/tasks")
@contest_redirect
async def tasks() -> str:
    if current_user.is_admin:
        tasks = await Task.all()
    else:
        tasks = await Task.filter(is_public=True)
    if await current_user.is_authenticated:
        solved_tasks = [
            submission.task for submission in
            await Submission.filter(author=current_user.user, first_solve=True).prefetch_related("task")
        ]
    else:
        solved_tasks = []
    return await render_template("tasks.html", title="Tasks", header="Tasks", tasks=tasks, solved_tasks=solved_tasks)


@main.route("/task/<string:task_id>")
@login_required  # Tasks are too cringe, hide from public
async def task_page(task_id: str) -> str:
    task = await Task.filter(task_id__iexact=task_id).prefetch_related("authors", "contests").first()
    if not task:
        abort(404)
    contest = await get_running_contest()
    if not (
            current_user.is_admin
            or task.is_public and not (contest and await contest.is_contestant(current_user))
            or contest and contest.status == "ongoing" and task in contest.tasks
            and await contest.is_contestant(current_user)
    ):
        abort(404)
    config = await get_config(task.task_id)
    batched = config and config["batched"]
    return await render_template(
        "task/task.html", title=task.task_id, task=task, test_cases=await get_test_cases(task.task_id),
        judge_is_online=await JudgeAPI.is_online(), sample_test_cases=await get_sample_test_cases(task.task_id),
        authors=join_authors(task.authors), contests=join_contests(task.contests), batched=batched
    )


@main.route("/task/<string:task_id>/submit", methods=["GET", "POST"])
@login_required
async def task_submit(task_id: str) -> Union[Response, str]:
    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)
    contest = await get_running_contest()
    test_cases = await get_test_cases(task.task_id)
    if not test_cases or not (
            current_user.is_admin
            or task.is_public and not (contest and await contest.is_contestant(current_user))
            or contest and contest.status == "ongoing" and task in contest.tasks
            and await contest.is_contestant(current_user)
    ) or not await JudgeAPI.is_online():
        abort(404)

    form = TaskSubmitForm()
    if form.validate_on_submit():
        if contest and contest.status == "prep":
            return redirect(url_for("main.contest_page", contest_id=contest.id))
        last_submission = await current_user.submissions.all().first()
        if (not current_user.is_admin  # Admin privileges
                and last_submission and datetime.now(utc) - last_submission.time <= timedelta(seconds=20)):
            await flash("You made a submission in the last 20 seconds. Please wait before submitting.", "danger")
        else:
            submission = await Submission.create(
                time=datetime.now(utc).replace(microsecond=0),
                task=task,
                author=current_user.user,
                language=form.language.data,
                source_code=form.source_code.data,
                contest=contest if contest and await contest.is_contestant(current_user) else None
            )

            asyncio.create_task(JudgeAPI.judge_submission(submission))
            return redirect(url_for("main.submission_page", submission_id=submission.id))
    elif request.method == "GET":
        form.language.data = current_user.language
    return await render_template(
        "task/task_submit.html", title=task.task_id, task=task,
        form=form, test_cases=test_cases, judge_is_online=True  # If offline, 404 already
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
    submissions = await submissions.offset((page - 1) * 50).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)
    return await render_template("submissions.html", title="Submissions", submissions=submissions,
                                 pagination=pagination, show_pagination=cnt > 50)


@main.route("/task/<string:task_id>/submissions")
async def task_submissions(task_id: str) -> str:
    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)
    contest = await get_running_contest()
    if not (
            current_user.is_admin
            or task.is_public and task.is_public and not (contest and await contest.is_contestant(current_user))
            or contest and contest.status == "ongoing" and task in contest.tasks
            and await contest.is_contestant(current_user)
    ):
        abort(404)
    submissions = task.submissions.all()
    if (contest and contest.status == "ongoing" and await contest.is_contestant(current_user)
            and not current_user.is_admin):
        submissions = submissions.filter(
            author=current_user.user, contest=contest)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset((page - 1) * 50).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)
    return await render_template(
        "task/task_submissions.html", title=f"{task.task_id}", task=task,
        test_cases=await get_test_cases(task.task_id), judge_is_online=await JudgeAPI.is_online(),
        submissions=submissions, pagination=pagination, show_pagination=cnt > 50
    )


@main.route("/user/<string:username>/submissions")
@contest_redirect
async def user_submissions(username: str) -> str:
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)
    if current_user.is_admin:
        submissions = user.submissions.all()
    else:
        submissions = user.submissions.filter(task__is_public=True)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset((page - 1) * 50).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)
    return await render_template("user/user_submissions.html", title=user.username, user=user, submissions=submissions,
                                 pagination=pagination, show_pagination=cnt > 50)


@main.route("/submission/<int:submission_id>")
async def submission_page(submission_id: int) -> str:
    submission = await Submission.filter(id=submission_id).prefetch_related(
        "task", "author", "test_case_results", "contest").first()
    if not submission:
        abort(404)
    contest = await get_running_contest()
    if not (
            current_user.is_admin
            or submission.task.is_public and not (contest and await contest.is_contestant(current_user))
            or contest and contest.status == "ongoing" and submission.task in contest.tasks
            and await contest.is_contestant(current_user) and submission.author.id == current_user.id
    ):
        abort(404)
    show_source_code = (
        await current_user.is_authenticated
        and (
            submission.author.id == current_user.id
            or current_user.is_admin
            # Solved
            or await current_user.submissions.filter(task=submission.task, first_solve=True).count()
        )
    )
    return await render_template("submission.html", title=f"Submission {submission.id}", submission=submission,
                                 show_source_code=show_source_code)


@cached(ttl=3)
async def get_leaderboard() -> List[Tuple[int, User]]:
    users = await User.filter(Q(is_student=True) | Q(is_admin=True)).order_by("-solves", "id")
    lb = []
    rank = 1
    for i in range(len(users)):
        if i != 0 and users[i].solves < users[i - 1].solves:
            rank = i + 1
        lb.append((rank, users[i]))
    return lb


@main.route("/leaderboard")
@contest_redirect
async def leaderboard() -> str:
    lb = await get_leaderboard()
    return await render_template("leaderboard.html", title="Leaderboard", users=lb)


@main.route("/user/<string:username>")
@login_required  # Do not expose user info to public
@contest_redirect
async def user_page(username: str) -> str:
    user = await User.filter(username__iexact=username).prefetch_related(
        "contest_participations__contest__tasks", "contest_participations__contest__participations",
        "authored_tasks").first()
    if not user:
        abort(404)

    # Contests
    show = [cp.contest.status == "ended" for cp in user.contest_participations]
    if user.contest_participations:
        await asyncio.gather(*[cp.contest.get_contestants_no() for cp in user.contest_participations])
        contest_dates = [cp.contest.start_time.date() for cp in user.contest_participations]

        async def get_contest_rank(contest_participation: ContestParticipation, index: int) -> Optional[int]:
            if not show[index]:
                return None
            points = await asyncio.gather(*[cp.total_points for cp in contest_participation.contest.participations])
            rank = len([p for p in points if p > await contest_participation.total_points]) + 1
            return rank

        contest_ranks = await asyncio.gather(
            *[get_contest_rank(cp, i) for i, cp in enumerate(user.contest_participations)]
        )
    else:
        contest_dates = []
        contest_ranks = []

    # Authored tasks
    authored_tasks = list(user.authored_tasks)
    authored_tasks = [task for task in authored_tasks if task.is_public]
    if authored_tasks:
        solved_tasks = [
            submission.task for submission in
            await Submission.filter(author=current_user.user, first_solve=True).prefetch_related("task")
        ]
    else:
        solved_tasks = []

    # Solved tasks
    # User might have solved non-public tasks which we count
    # So we let the denominator be the union of public tasks and solved tasks
    submissions = await user.submissions.filter(first_solve=True).only("task_id")
    submission_task_ids = [submission.task_id for submission in submissions]
    task_count = await Task.filter(Q(is_public=True) | Q(id__in=submission_task_ids)).count()

    submission_count = await user.submissions.all().count()

    return await render_template(
        "user/user.html", title=user.username, user=user, show=show, contest_dates=contest_dates,
        contest_ranks=contest_ranks, authored_tasks=authored_tasks, solved_tasks=solved_tasks, task_count=task_count,
        submission_count=submission_count
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
        "contests.html", title="Contests", contests=zip(
            contests, [[contestant.id for contestant in c]
                       for c in contestants]
        ), pagination=pagination, show_pagination=cnt > 50
    )


@main.route("/contest/<int:contest_id>")
async def contest_page(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id).prefetch_related(
        "tasks", "participations__task_points__task").first()
    if not contest:
        abort(404)
    running_contest = await get_running_contest()
    if (running_contest and contest != running_contest and not current_user.is_admin
            and await running_contest.is_contestant(current_user)):
        abort(404)

    # Prepare scoreboard of current user
    contest_task_points = []
    first_solves = []
    contest_participation = None
    if await current_user.is_authenticated:
        contest_participation = await contest.participations.filter(
            contestant=current_user.user).prefetch_related("task_points").first()
        if contest_participation:
            for task in contest.tasks:
                ctp = [
                    ctp for ctp in contest_participation.task_points if ctp.task_id == task.id]
                contest_task_points.append(ctp[0] if ctp else None)
                first_solve = await contest.submissions.filter(
                    author=current_user.user, task=task, first_solve=True).first()
                first_solves.append(
                    first_solve.time - contest.start_time if first_solve else None)

    # Load subtask points of each contest task
    points = []
    for task in contest.tasks:
        config = await get_config(task.task_id)
        points.append(config["points"]
                      if config and "points" in config else [100])

    # Calculate contest statistics
    stats = {task.task_id: {"attempts": 0, "data": []}
             for task in contest.tasks}
    stats["overall"] = {"attempts": 0, "data": []}
    for cp in contest.participations:
        if cp.task_points:
            stats["overall"]["attempts"] += 1
            stats["overall"]["data"].append(await cp.total_points)
            for ctp in cp.task_points:
                stats[ctp.task.task_id]["attempts"] += 1
                stats[ctp.task.task_id]["data"].append(ctp.total_points)
    for key in stats:
        stats[key]["max"] = max(stats[key]["data"], default="--")
        stats[key]["max_cnt"] = stats[key]["data"].count(
            stats[key]["max"]) if stats[key]["attempts"] else "--"
        stats[key]["mean"] = mean(
            stats[key]["data"]) if stats[key]["attempts"] else "--"
        stats[key]["median"] = median(
            stats[key]["data"]) if stats[key]["attempts"] else "--"
        stats[key]["sd"] = pstdev(
            stats[key]["data"]) if stats[key]["attempts"] else "--"

    show_links = (
        contest.status == "ongoing" and (current_user.is_admin or await contest.is_contestant(current_user))
        or contest.status == "ended" and (current_user.is_admin or await contest.is_contestant(current_user)
                                          or all(task.is_public for task in contest.tasks))
    )
    show_stats = (
        contest.status == "ongoing" and current_user.is_admin
        or contest.status == "ended" and (current_user.is_admin or await contest.is_contestant(current_user)
                                          or all(task.is_public for task in contest.tasks))
    )
    return await render_template(
        "contest/contest.html", title=contest.title, contest=contest, contest_participation=contest_participation,
        contest_task_points=tuple(zip(contest_task_points, points)), contest_tasks_count=len(contest.tasks),
        first_solves=first_solves, stats=stats, show_links=show_links, show_stats=show_stats
    )


@main.route("/contest/<int:contest_id>/join", methods=["POST"])
@contest_redirect
async def contest_join(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).first()
    if not contest:
        abort(404)
    if not (contest.is_public and contest.status == "pre_prep" and await current_user.is_authenticated
            and not await contest.is_contestant(current_user)):
        abort(400)
    await ContestParticipation.create(contest=contest, contestant=current_user.user)
    await flash("Successfully joined.", "success")
    return redirect(url_for("main.contest_page", contest_id=contest.id))


@main.route("/contest/<int:contest_id>/leave", methods=["POST"])
@contest_redirect
async def contest_leave(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).first()
    if not contest:
        abort(404)
    if not (contest.is_public and contest.status == "pre_prep" and await current_user.is_authenticated
            and await contest.is_contestant(current_user)):
        abort(400)
    await contest.participations.filter(contestant=current_user.user).delete()
    await flash("Successfully left.", "success")
    return redirect(url_for("main.contest_page", contest_id=contest.id))


@main.route("/contest/<int:contest_id>/submissions")
async def contest_submissions(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id).prefetch_related("tasks").first()
    if not (
            contest
            and (
                contest.status == "ongoing" and (current_user.is_admin or await contest.is_contestant(current_user))
                or contest.status == "ended" and (current_user.is_admin or await contest.is_contestant(current_user)
                                                  or all(task.is_public for task in contest.tasks))
                # All contest tasks must be public for contests submissions to show for non-admin non-contestants
            )
    ):
        abort(404)
    running_contest = await get_running_contest()
    if (running_contest and contest != running_contest and not current_user.is_admin
            and await running_contest.is_contestant(current_user)):
        abort(404)
    if current_user.is_admin:
        submissions = contest.submissions.all()
    elif contest.status == "ongoing" and await contest.is_contestant(current_user):
        submissions = contest.submissions.filter(author=current_user.user)
    else:
        submissions = contest.submissions.filter(task__is_public=True)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset((page - 1) * 50).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)

    show_links = (
        contest.status == "ongoing" and (current_user.is_admin or await contest.is_contestant(current_user))
        or contest.status == "ended" and (current_user.is_admin or await contest.is_contestant(current_user)
                                          or all(task.is_public for task in contest.tasks))
    )
    return await render_template("contest/contest_submissions.html", title=contest.title, contest=contest,
                                 submissions=submissions, pagination=pagination, show_pagination=cnt > 50,
                                 show_links=show_links)


@main.route("/contest/<int:contest_id>/results")
async def contest_results(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id).prefetch_related("tasks").first()
    if not (
            contest
            and (
                contest.status == "ongoing" and (current_user.is_admin or await contest.is_contestant(current_user))
                or contest.status == "ended" and (current_user.is_admin or await contest.is_contestant(current_user)
                                                  or all(task.is_public for task in contest.tasks))
                # All contest tasks must be public for contests results to show for non-admin non-contestants
            )
    ):
        abort(404)
    running_contest = await get_running_contest()
    if (running_contest and contest != running_contest and not current_user.is_admin
            and await running_contest.is_contestant(current_user)):
        abort(404)
    contest_participations = await contest.participations.all().prefetch_related("task_points", "contestant")
    # Load all points first
    await asyncio.gather(*[cp.total_points for cp in contest_participations])

    # Sort contest participations by points then username
    cp_sort_key = {cp: (-await cp.total_points, cp.contestant.username) for cp in contest_participations}
    contest_participations.sort(key=cp_sort_key.__getitem__)

    ranked_cp = []  # Contest participations with ranks
    contest_task_points = []  # Points of each task of each contestant
    # Stores first solve of each task of each contestant then timedelta taken to solve
    first_solves = []
    rank = 1

    for i in range(len(contest_participations)):
        if i != 0 and await contest_participations[i].total_points < await contest_participations[i - 1].total_points:
            rank = i + 1
        ranked_cp.append((rank, contest_participations[i]))
        contest_task_points.append([])
        first_solves.append([])
        for task in contest.tasks:
            # Find corresponding contest task points for task
            ctp = [
                ctp for ctp in contest_participations[i].task_points if ctp.task_id == task.id]
            contest_task_points[-1].append(ctp[0] if ctp else None)

            # Cannot create task with QuerySet directly (despite awaitable) so it is wrapped in async function
            async def get_first_solve(task_id: int, contestant_id: int) -> Optional[Submission]:
                return await Submission.filter(
                    task_id=task_id, author_id=contestant_id, first_solve=True, contest=contest).first()

            # Get first solve of current contestant and task later
            first_solves[-1].append(asyncio.create_task(
                get_first_solve(
                    task.id, contest_participations[i].contestant_id)
            ))

    # For each contestant-task pair, retrieve first solve and calculate timedelta taken to solve (if solve exists)
    for i in range(len(contest_participations)):
        for j in range(len(contest.tasks)):
            first_solve = await first_solves[i][j]
            first_solves[i][j] = first_solve.time - \
                contest.start_time if first_solve else None

    # First solve of each task
    contest_first_solves = await asyncio.gather(
        *[task.submissions.filter(first_solve=True, contest=contest).prefetch_related("author").order_by("id").first()
          for task in contest.tasks]
    )
    # Contestants who submitted the solved each task first
    contest_first_solve_contestants = [first_solve.author if first_solve else None
                                       for first_solve in contest_first_solves]

    show_links = (
        contest.status == "ongoing" and (current_user.is_admin or await contest.is_contestant(current_user))
        or contest.status == "ended" and (current_user.is_admin or await contest.is_contestant(current_user)
                                          or all(task.is_public for task in contest.tasks))
    )
    return await render_template(
        "contest/contest_results.html", title=contest.title, contest=contest, ranked_cp=ranked_cp,
        contest_task_points=contest_task_points, first_solves=first_solves, contest_tasks_count=len(
            contest.tasks),
        contest_first_solve_contestants=contest_first_solve_contestants, show_links=show_links
    )


@main.route("/info")
@contest_redirect
async def info() -> str:
    return await render_template("info.html", title="Info", version=__version__)


@main.route("/buyAccount")
async def buy_account() -> str:
    return await render_template("buy_account.html", title="Buy Account")


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
            return redirect(next_page if next_page and is_safe_url(next_page) else url_for("main.home"))
        await flash("Login unsuccessful.", "danger")
    return await render_template("login.html", title="Login", form=form)


@main.route("/logout")
async def logout() -> Response:
    logout_user()
    return redirect(url_for("main.home"))


@main.route("/settings", methods=["GET", "POST"])
@contest_redirect
@login_required
async def settings() -> Union[Response, str]:
    settings_form = StudentSettingsForm(
    ) if current_user.is_student else NonStudentSettingsForm()
    reset_password_form = ResetPasswordForm()
    if "profile_pic" in await request.files:
        settings_form.profile_pic.data = (await request.files)["profile_pic"]
    if settings_form.submit.data and await validate(settings_form):
        current_user.language = settings_form.language.data
        if not current_user.can_edit_profile:
            current_user.language = settings_form.language.data
            await current_user.save()
            await flash("Settings updated.", "success")
            return redirect(url_for("main.settings"))

        fn_40 = fn_160 = None
        if settings_form.profile_pic.data:
            try:
                fn_40, fn_160 = await save_picture(settings_form.profile_pic.data)
            except:
                pass
        old_fn_40, old_fn_160 = current_user.img_40, current_user.img_160

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
        if bcrypt.check_password_hash(current_user.password, reset_password_form.current_password.data):
            # Allows old pw = new pw, whatever
            current_user.password = bcrypt.generate_password_hash(
                reset_password_form.new_password.data).decode("utf-8")
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
            await flash("You have been restricted from editing your profile.", "danger")
    return await render_template("settings.html", title="Settings",
                                 settings_form=settings_form, reset_password_form=reset_password_form)
