import asyncio
from typing import List, Union

from pytz import utc
from quart import (
    Blueprint, Markup, Response, abort, current_app,
    flash, redirect, render_template, request, url_for
)
from quart_auth import current_user
from tortoise.expressions import F
from tortoise.fields import ReverseRelation

from wykoj import bcrypt
from wykoj.api import JudgeAPI
from wykoj.blueprints.api.judge import recalculate_contest_task_points
from wykoj.blueprints.utils.access import admin_only
from wykoj.blueprints.utils.misc import get_page, remove_pfps, save_picture
from wykoj.blueprints.utils.pagination import Pagination
from wykoj.constants import Verdict, hkt
from wykoj.forms.admin import (
    AdminResetPasswordForm, ContestForm, NewContestForm,
    NewNonStudentUserForm, NewStudentUserForm, SidebarForm, TaskForm, UserForm
)
from wykoj.models import Contest, ContestParticipation, Sidebar, Submission, Task, User

admin = Blueprint("admin", __name__, url_prefix="/admin")


@admin.route("/")
@admin_only
async def home() -> str:
    return await render_template("admin/home.html", title="Home")


@admin.route("/sidebar", methods=["GET", "POST"])
@admin_only
async def sidebar() -> str:
    """Allow admins to edit the HTML of home page sidebar."""
    sidebar = await Sidebar.get()
    form = SidebarForm()
    if form.validate_on_submit():
        sidebar.content = form.content.data.strip()
        await sidebar.save()
        await flash("Sidebar updated.", "success")
    elif request.method == "GET":
        form.content.data = sidebar.content
    return await render_template("admin/sidebar.html", title="Sidebar", form=form)


@admin.route("/tasks")
@admin_only
async def tasks() -> str:
    tasks = Task.all().order_by("task_id")
    cnt = await tasks.count()
    page = get_page()
    tasks = await tasks.offset((page - 1) * 50).limit(50)
    pagination = Pagination(tasks, page=page, per_page=50, total=cnt)
    return await render_template(
        "admin/tasks.html",
        title="Tasks",
        tasks=tasks,
        pagination=pagination,
        show_pagination=cnt > 50
    )


@admin.route("/task/new", methods=["GET", "POST"])
@admin_only
async def new_task() -> Union[Response, str]:
    form = TaskForm()
    if await form.full_validate():
        usernames = [a.strip() for a in form.authors.data.split(",") if a.strip()]
        authors = await asyncio.gather(
            *[User.filter(username__iexact=a).first() for a in usernames]
        )
        task = Task(
            task_id=form.task_id.data,
            title=form.title.data,
            is_public=form.is_public.data,
            content=form.content.data,
            time_limit=form.time_limit.data,
            memory_limit=form.memory_limit.data
        )
        await task.save()
        await task.authors.add(*authors)
        await flash(
            Markup(
                f'Task {task.task_id} created. '
                f'Create <a href="{current_app.config["TEST_CASES_GITHUB"]}">test cases</a> '
                f'inside the directory {task.task_id}.'
            ), "success"
        )
        return redirect(url_for("admin.tasks"))
    elif request.method == "GET":
        # Recommended values
        form.authors.data = current_user.username
        form.time_limit.data = 1
        form.memory_limit.data = 64
    return await render_template("admin/task.html", title="New Task", form=form, task=None)


@admin.route("/task/<string:task_id>", methods=["GET", "POST"])
@admin_only
async def task_page(task_id: str) -> Union[Response, str]:
    task = await Task.filter(task_id__iexact=task_id).prefetch_related("authors").first()
    if not task:
        abort(404)
    form = TaskForm(id=task.task_id)
    if await form.full_validate():
        usernames = [a.strip() for a in form.authors.data.split(",") if a.strip()]
        usernames = sorted(set(usernames))  # Delete duplicates
        authors = await asyncio.gather(
            *[User.filter(username__iexact=username).first() for username in usernames]
        )
        authors = [a for a in authors if a]

        task.task_id = form.task_id.data
        task.title = form.title.data
        task.is_public = form.is_public.data
        task.content = form.content.data.strip()
        task.time_limit = form.time_limit.data
        task.memory_limit = form.memory_limit.data
        await task.save()

        await task.authors.clear()
        await task.authors.add(*authors)

        await flash(f"Task {task.task_id} updated.", "success")
        return redirect(url_for("admin.tasks"))
    elif request.method == "GET":
        form.id.data = task.id
        form.task_id.data = task.task_id
        form.title.data = task.title
        form.is_public.data = task.is_public
        form.authors.data = ",".join([a.username for a in task.authors])
        form.content.data = task.content
        form.time_limit.data = task.time_limit
        form.memory_limit.data = task.memory_limit
    return await render_template(
        "admin/task.html", title=f"{task.task_id} - {task.title}", form=form, task=task
    )


@admin.route("/task/<string:task_id>/delete", methods=["POST"])
@admin_only
async def delete_task(task_id: str) -> Response:
    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)
    await task.delete()  # Submissions are cascade deleted
    asyncio.create_task(_recalc_solves())
    await flash("Task deleted.", "success")
    return redirect(url_for("admin.tasks"))


@admin.route("/users")
@admin_only
async def users() -> str:
    users = User.all().order_by("username")
    cnt = await users.count()
    page = get_page()
    users = await users.offset((page - 1) * 50).limit(50)
    pagination = Pagination(users, page=page, per_page=50, total=cnt)
    return await render_template(
        "admin/users.html",
        title="Users",
        users=users,
        pagination=pagination,
        show_pagination=cnt > 50
    )


@admin.route("/user/new", methods=["GET", "POST"])
@admin_only
async def new_user() -> Union[Response, str]:
    if request.args.get("student") == "false":
        form = NewNonStudentUserForm()
    else:
        form = NewStudentUserForm()
    if await form.full_validate():
        password_hash = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        await User.create(
            username=form.username.data,
            name=form.english_name.data,
            english_name=form.english_name.data,
            password=password_hash,
            is_student=type(form) == NewStudentUserForm,
            is_admin=form.is_admin.data
        )
        await flash("User created.", "success")
        return redirect(url_for("admin.users"))
    return await render_template(
        "admin/new_user.html",
        form=form,
        title=f"New {'Non-' if request.args.get('student') == 'false' else ''}Student User"
    )


@admin.route("/user/<string:username>", methods=["GET", "POST"])
@admin_only
async def user_page(username: str) -> Union[Response, str]:
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)
    user_form = UserForm()
    reset_password_form = AdminResetPasswordForm()
    if "profile_pic" in await request.files:
        user_form.profile_pic.data = (await request.files)["profile_pic"]
    if user_form.submit.data and await user_form.full_validate():
        fn_40 = fn_160 = None
        if user_form.profile_pic.data:
            try:
                fn_40, fn_160 = await save_picture(user_form.profile_pic.data)
            except Exception:
                pass
        old_fn_40, old_fn_160 = user.img_40, user.img_160

        user.username = user_form.username.data
        user.name = user_form.name.data or user_form.username.data
        user.english_name = user_form.english_name.data
        user.chesscom_username = user_form.chesscom_username.data
        user.language = user_form.language.data
        user.img_40 = fn_40 or user.img_40
        user.img_160 = fn_160 or user.img_160
        user.can_edit_profile = user_form.can_edit_profile.data
        user.is_student = user_form.is_student.data
        user.is_admin = user_form.is_admin.data
        await user.save()

        # Delete old profile pics if they were not the default pics
        if fn_40 and old_fn_40 != "default_40.png":
            await remove_pfps(old_fn_40, old_fn_160)

        await flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    elif reset_password_form.save.data and reset_password_form.validate_on_submit():
        user.password = bcrypt.generate_password_hash(reset_password_form.new_password.data
                                                      ).decode("utf-8")
        await user.save()
        await flash("Password updated.", "success")
        return redirect(url_for("admin.users"))
    elif request.method == "GET":
        user_form.id.data = user.id
        user_form.username.data = user.username
        user_form.name.data = user.name
        user_form.english_name.data = user.english_name
        user_form.chesscom_username.data = user.chesscom_username
        user_form.language.data = user.language
        user_form.can_edit_profile.data = user.can_edit_profile
        user_form.is_student.data = user.is_student
        user_form.is_admin.data = user.is_admin
    return await render_template(
        "admin/user.html",
        title=user.name,
        user_form=user_form,
        reset_password_form=reset_password_form,
        user=user
    )


@admin.route("/user/<string:username>/delete", methods=["POST"])
@admin_only
async def delete_user(username: str) -> Response:
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)
    await user.delete()  # Submissions are cascade deleted
    await flash("User deleted.", "success")
    return redirect(url_for("admin.users"))


@admin.route("/user/<string:username>/resetProfile", methods=["POST"])
@admin_only
async def reset_profile(username: str) -> Response:
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)
    old_fn_40, old_fn_160 = user.img_40, user.img_160
    user.name = user.username
    user.img_40 = "default_40.png"
    user.img_160 = "default_160.png"
    await user.save()

    # Delete old profile pics if they were not the default pics
    if old_fn_40 != "default_40.png":
        await remove_pfps(old_fn_40, old_fn_160)

    await flash("Profile reset.", "success")
    return redirect(url_for("admin.users"))


async def reset_submission(submission: Submission) -> None:
    submission.verdict = Verdict.PENDING
    submission.score = 0
    submission._subtask_scores = None
    submission.time_used = None
    submission.memory_used = None
    submission.first_solve = False
    await submission.save()
    await submission.test_case_results.all().delete()


@admin.route("/submission/<int:submission_id>/rejudge", methods=["POST"])
@admin_only
async def rejudge_submission(submission_id: int) -> Response:
    submission = await Submission.filter(id=submission_id).prefetch_related("task",
                                                                            "author").first()
    if not submission:
        abort(404)
    if submission.first_solve:
        await asyncio.gather(
            Task.filter(id=submission.task.id).update(solves=F("solves") - 1),
            User.filter(id=submission.author.id).update(solves=F("solves") - 1)
        )
    await reset_submission(submission)

    current_app.add_background_task(JudgeAPI.judge_submission, submission)
    await flash("Rejudging submission...", "success")
    return redirect(url_for("main.submission_page", submission_id=submission.id))


async def _rejudge_submissions(
    submissions: Union[List[Submission], ReverseRelation[Submission]]
) -> None:
    await asyncio.gather(
        *[submission.fetch_related("task", "author") for submission in submissions]
    )
    submissions = sorted(submissions, key=lambda s: s.id)

    await asyncio.gather(*[reset_submission(submission) for submission in submissions])
    for submission in submissions:
        current_app.add_background_task(JudgeAPI.judge_submission, submission)
    await _recalc_solves()


@admin.route("/task/<string:task_id>/rejudge", methods=["POST"])
@admin_only
async def rejudge_task_submissions(task_id: str) -> Response:
    task = await Task.filter(task_id__iexact=task_id).prefetch_related("submissions").first()
    if not task:
        abort(404)

    asyncio.create_task(_rejudge_submissions(task.submissions))
    await flash("Rejudging submissions...", "success")
    return redirect(url_for("main.task.submissions_page", task_id=task.task_id))


@admin.route("/contest/<int:contest_id>/rejudge", methods=["POST"])
@admin_only
async def rejudge_contest_submissions(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).prefetch_related("submissions").first()
    if not contest:
        abort(404)

    asyncio.create_task(_rejudge_submissions(contest.submissions))
    await flash("Rejudging submissions...", "success")
    return redirect(url_for("main.contest.submissions_page", contest_id=contest.id))


@admin.route("/recalc_solves", methods=["POST"])
@admin_only
async def recalc_solves() -> Response:
    asyncio.create_task(_recalc_solves())
    await flash("Recalculating solves.", "success")
    return redirect(url_for("admin.home"))


async def _recalc_solves() -> None:
    async def _recalc_task_solves(task: Task) -> None:
        task.solves = await task.submissions.filter(first_solve=True).count()
        await task.save()

    async def _recalc_user_solves(user: User) -> None:
        user.solves = await user.submissions.filter(first_solve=True).count()
        await user.save()

    async for task in Task.all().prefetch_related("submissions"):
        asyncio.create_task(_recalc_task_solves(task))
    async for user in User.all().prefetch_related("submissions"):
        asyncio.create_task(_recalc_user_solves(user))


async def _delete_submission(submission: Submission) -> None:
    first_solve = submission.first_solve
    await submission.delete()
    if first_solve:
        solve = await Submission.filter(
            task_id=submission.task_id, author_id=submission.author_id, verdict=Verdict.ACCEPTED
        ).order_by("id").first()  # Previous solve
        if solve:
            solve.first_solve = True
            await solve.save()
        else:
            await asyncio.gather(
                Task.filter(id=submission.task_id).update(solves=F("solves") - 1),
                User.filter(id=submission.author_id).update(solves=F("solves") - 1)
            )

    if submission.contest:
        contest_participation = [
            cp for cp in submission.contest.participations
            if cp.contestant_id == submission.author_id
        ][0]
        await contest_participation.fetch_related("task_points")
        await recalculate_contest_task_points(contest_participation, submission.task)


@admin.route("/submission/<int:submission_id>/delete", methods=["POST"])
@admin_only
async def delete_submission(submission_id: int) -> Response:
    submission = await Submission.filter(id=submission_id).prefetch_related("contest").first()
    if not submission:
        abort(404)
    await _delete_submission(submission)
    await flash("Submission deleted.", "success")
    return redirect(url_for("main.submissions"))


@admin.route("/contests")
@admin_only
async def contests() -> str:
    contests = Contest.all()
    cnt = await contests.count()
    page = get_page()
    contests = await contests.offset((page - 1) * 50).limit(50)
    pagination = Pagination(contests, page=page, per_page=50, total=cnt)
    return await render_template(
        "admin/contests.html",
        title="Contests",
        contests=contests,
        pagination=pagination,
        show_pagination=cnt > 50
    )


@admin.route("/contest/new", methods=["GET", "POST"])
@admin_only
async def new_contest() -> Union[Response, str]:
    form = NewContestForm()
    if await form.full_validate():
        task_ids = [task_id.strip() for task_id in form.tasks.data.split(",") if task_id.strip()]
        task_ids = sorted(set(task_ids))  # Delete duplicates
        tasks = await asyncio.gather(
            *[Task.filter(task_id__iexact=task_id).first() for task_id in task_ids]
        )
        tasks = [t for t in tasks if t]

        contest = await Contest.create(
            title=form.title.data,
            is_public=form.is_public.data,
            start_time=hkt.localize(form.start_time.data).astimezone(utc),
            duration=form.duration.data
        )
        await contest.tasks.add(*tasks)

        await flash("Contest created.", "success")
        return redirect(url_for("admin.contests"))
    return await render_template("admin/contest.html", title="New Contest", form=form)


@admin.route("/contest/<int:contest_id>", methods=["GET", "POST"])
@admin_only
async def contest_page(contest_id: int) -> Union[Response, str]:
    contest = await Contest.filter(id=contest_id
                                   ).prefetch_related("participations__contestant", "tasks").first()
    if not contest:
        abort(404)
    form = ContestForm()
    if await form.full_validate():
        task_ids = [task_id.strip() for task_id in form.tasks.data.split(",") if task_id.strip()]
        task_ids = sorted(set(task_ids))  # Delete duplicates
        tasks = await asyncio.gather(
            *[Task.filter(task_id__iexact=task_id).first() for task_id in task_ids]
        )
        tasks = [t for t in tasks if t]

        contest.title = form.title.data
        contest.is_public = form.is_public.data
        contest.start_time = hkt.localize(form.start_time.data).astimezone(utc)
        contest.duration = form.duration.data
        contest.publish_editorial = form.publish_editorial.data
        contest.editorial_content = form.editorial_content.data.strip()
        await contest.save()

        # Update carefully
        to_remove = [task for task in contest.tasks if task not in tasks]
        if to_remove:
            await contest.tasks.remove(*to_remove)
        await contest.tasks.add(*tasks)

        usernames = [
            username.strip() for username in form.contestants.data.split(",") if username.strip()
        ]
        usernames = sorted(set(usernames))
        users = await asyncio.gather(
            *[User.filter(username__iexact=username).first() for username in usernames]
        )
        users = [u for u in users if u]
        coros = []
        for contest_participation in contest.participations:
            if contest_participation.contestant in users:  # Existing contestants
                users.remove(contest_participation.contestant)
            else:  # Removed contestants
                coros.append(contest_participation.delete())
        for user in users:  # New contestants
            coros.append(ContestParticipation(contest=contest, contestant=user).save())
        if coros:
            await asyncio.gather(*coros)
        await flash("Contest updated.", "success")
        return redirect(url_for("admin.contests"))
    elif request.method == "GET":
        form.id.data = contest.id
        form.title.data = contest.title
        form.is_public.data = contest.is_public
        form.start_time.data = contest.start_time.astimezone(hkt)
        form.duration.data = contest.duration
        form.tasks.data = ",".join([t.task_id for t in contest.tasks])
        form.contestants.data = ",".join([cp.contestant.username for cp in contest.participations])
        form.publish_editorial.data = contest.publish_editorial
        form.editorial_content.data = contest.editorial_content
    return await render_template(
        "admin/contest.html", title=contest.title, form=form, contest=contest
    )


@admin.route("/contest/<int:contest_id>/delete", methods=["POST"])
@admin_only
async def delete_contest(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).first()
    if not contest:
        abort(404)
    await contest.delete()
    await flash("Contest deleted.", "success")
    return redirect(url_for("admin.contests"))


@admin.route("/guide")
@admin_only
async def guide() -> str:
    return await render_template("admin/guide.html", title="Guide")
