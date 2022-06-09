from datetime import datetime, timedelta
from typing import Union

from pytz import utc
from quart import (
    Blueprint, Response, abort, current_app, flash, g, redirect, render_template, request, url_for
)
from quart_auth import current_user, login_required

from wykoj.api import JudgeAPI, TestCaseAPI
from wykoj.blueprints.utils.misc import get_page, get_running_contest, join_authors, join_contests
from wykoj.blueprints.utils.pagination import Pagination
from wykoj.constants import ContestStatus
from wykoj.forms.main import TaskSubmitForm
from wykoj.models import Submission, Task

task_blueprint = Blueprint("task", __name__, url_prefix="/task/<string:task_id>")


@task_blueprint.before_request
async def before_request() -> None:
    task_id = request.view_args["task_id"]
    task = await Task.filter(task_id__iexact=task_id).first()
    if not task:
        abort(404)

    contest = await get_running_contest()
    if not (
        current_user.is_admin
        or task.is_public and not (contest and await contest.is_contestant(current_user))
        or contest and contest.status == ContestStatus.ONGOING and task in contest.tasks
        and await contest.is_contestant(current_user)
    ):
        abort(404)

    g.test_cases_ready = await TestCaseAPI.check_test_cases_ready(task.task_id)
    g.judge_is_online = JudgeAPI.is_online()
    g.solved = await current_user.is_authenticated and bool(
        await Submission.filter(task_id=task.id, author_id=current_user.id,
                                first_solve=True).first()
    )


@task_blueprint.route("/")
async def task_page(task_id: str) -> str:
    task = await Task.filter(task_id__iexact=task_id).prefetch_related("authors",
                                                                       "contests").first()

    config = await TestCaseAPI.get_config(task.task_id)
    batched = config and config["batched"]
    return await render_template(
        "task/task.html",
        title=f"Task {task.task_id} - {task.title}",
        task=task,
        sample_test_cases=await TestCaseAPI.get_sample_test_cases(task.task_id),
        authors=join_authors(task.authors),
        contests=join_contests(task.contests),
        batched=batched
    )


@task_blueprint.route("/submit", methods=["GET", "POST"])
@login_required
async def submit(task_id: str) -> Union[Response, str]:
    task = await Task.filter(task_id__iexact=task_id).first()
    contest = await get_running_contest()
    if not g.test_cases_ready or not g.judge_is_online:
        abort(404)

    form = TaskSubmitForm()
    if await form.full_validate():
        last_submission = await current_user.submissions.all().first()
        if (
            not current_user.is_admin  # Admin supremacy
            and last_submission
            and datetime.now(utc) - last_submission.time <= timedelta(seconds=10)
        ):
            await flash(
                "You made a submission in the last 10 seconds. Please wait before submitting.",
                "danger"
            )
        else:
            if form.source_code_file.data:
                try:
                    source_code = form.source_code_file.data.read().decode()
                except UnicodeDecodeError:
                    abort(418)
            else:
                source_code = form.source_code.data

            submission = await Submission.create(
                time=datetime.now(utc).replace(microsecond=0),
                task=task,
                author=current_user.user,
                language=form.language.data,
                source_code=source_code,
                contest=contest if contest and await contest.is_contestant(current_user) else None
            )

            current_app.add_background_task(JudgeAPI.judge_submission, submission)
            return redirect(url_for("main.submission_page", submission_id=submission.id))
    elif request.method == "GET":
        form.language.data = current_user.language

    return await render_template(
        "task/task_submit.html", title=f"Submit - Task {task.task_id}", task=task, form=form
    )


@task_blueprint.route("/submissions")
async def submissions_page(task_id: str) -> str:
    task = await Task.filter(task_id__iexact=task_id).first()
    contest = await get_running_contest()

    submissions = task.submissions.all()
    if (
        contest and contest.status == ContestStatus.ONGOING
        and await contest.is_contestant(current_user) and not current_user.is_admin
    ):
        submissions = submissions.filter(author=current_user.user, contest=contest)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset(
        (page - 1) * 50
    ).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)

    return await render_template(
        "task/task_submissions.html",
        title=f"Submissions - Task {task.task_id}",
        task=task,
        submissions=submissions,
        pagination=pagination,
        show_pagination=cnt > 50
    )
