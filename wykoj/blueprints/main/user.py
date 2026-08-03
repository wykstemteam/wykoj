import asyncio

from quart import Blueprint, abort, render_template, request
from quart_auth import current_user, login_required
from tortoise.expressions import Q
from tortoise.functions import Count

from wykoj.blueprints.utils.access import contest_redirect
from wykoj.blueprints.utils.misc import get_page
from wykoj.blueprints.utils.pagination import Pagination
from wykoj.constants import ContestStatus
from wykoj.models import Submission, Task, User

user_blueprint = Blueprint("user", __name__, url_prefix="/user/<string:username>")


@user_blueprint.before_request
async def before_request() -> None:
    username = request.view_args["username"]
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)


@user_blueprint.route("/")
@login_required  # Do not expose user info to public
@contest_redirect
async def user_page(username: str) -> str:
    user = await User.filter(username__iexact=username).prefetch_related(
        "contest_participations__contest__tasks", "authored_tasks"
    ).first()

    # Contests
    # Templates render in async mode, so reading a Tortoise relation from one
    # (cp.contest, cp.contest.tasks, ...) awaits it, and awaiting a relation
    # re-runs its query every time, even when it was already prefetched. Build
    # plain values here so the template never touches an ORM object.
    total_points = await asyncio.gather(
        *[cp.total_points for cp in user.contest_participations]
    )
    contest_rows = [
        {
            "contest_id": cp.contest.id,
            "title": cp.contest.title,
            "date": cp.contest.start_time.date(),
            "ended": cp.contest.status == ContestStatus.ENDED,
            "total_points": points,
            "max_points": len(cp.contest.tasks) * 100,
        } for cp, points in zip(user.contest_participations, total_points)
    ]

    # Authored tasks
    authored_tasks = list(user.authored_tasks)
    authored_tasks = [task for task in authored_tasks if task.is_public]
    if authored_tasks:
        solved_tasks = [
            submission.task for submission in await
            Submission.filter(author=current_user.user, first_solve=True).prefetch_related("task")
        ]
        attempt_counts = await Submission.filter(
            task_id__in=[task.id for task in authored_tasks]
        ).annotate(count=Count("author_id", distinct=True)).group_by("task_id").values(
            "task_id", "count"
        )
        attempts = {row["task_id"]: row["count"] for row in attempt_counts}
    else:
        solved_tasks = []
        attempts = {}

    # Solved tasks
    # User might have solved non-public tasks which we count
    # So we let the denominator be the union of public tasks and solved tasks
    submissions = await user.submissions.filter(first_solve=True).only("task_id")
    submission_task_ids = [submission.task_id for submission in submissions]
    task_count = await Task.filter(Q(is_public=True) | Q(id__in=submission_task_ids)).count()

    submission_count = await user.submissions.all().count()

    return await render_template(
        "user/user.html",
        title=f"User {user.username} - {user.name}",
        user=user,
        contest_rows=contest_rows,
        authored_tasks=authored_tasks,
        solved_tasks=solved_tasks,
        attempts=attempts,
        task_count=task_count,
        submission_count=submission_count
    )


@user_blueprint.route("/submissions")
@contest_redirect
async def submissions_page(username: str) -> str:
    user = await User.filter(username__iexact=username).first()

    if current_user.is_admin:
        submissions = user.submissions.all()
    else:
        submissions = user.submissions.filter(task__is_public=True)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset(
        (page - 1) * 50
    ).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)
    return await render_template(
        "user/user_submissions.html",
        title=f"Submissions - User {user.username}",
        user=user,
        submissions=submissions,
        pagination=pagination,
        show_pagination=cnt > 50
    )
