import asyncio
from typing import Optional

from quart import Blueprint, abort, render_template, request
from quart_auth import current_user, login_required
from tortoise.query_utils import Q

from wykoj.blueprints.utils.access import contest_redirect
from wykoj.blueprints.utils.misc import get_page
from wykoj.blueprints.utils.pagination import Pagination
from wykoj.constants import ContestStatus
from wykoj.models import ContestParticipation, Submission, Task, User

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
        "contest_participations__contest__tasks", "contest_participations__contest__participations",
        "authored_tasks"
    ).first()

    # Contests
    show = [cp.contest.status == ContestStatus.ENDED for cp in user.contest_participations]
    if user.contest_participations:
        await asyncio.gather(
            *[cp.contest.get_contestants_no() for cp in user.contest_participations]
        )
        contest_dates = [cp.contest.start_time.date() for cp in user.contest_participations]

        async def get_contest_rank(contest_participation: ContestParticipation,
                                   index: int) -> Optional[int]:
            if not show[index]:
                return None
            points = await asyncio.gather(
                *[cp.total_points for cp in contest_participation.contest.participations]
            )
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
            submission.task for submission in await
            Submission.filter(author=current_user.user, first_solve=True).prefetch_related("task")
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
        "user/user.html",
        title=f"User {user.username} - {user.name}",
        user=user,
        show=show,
        contest_dates=contest_dates,
        contest_ranks=contest_ranks,
        authored_tasks=authored_tasks,
        solved_tasks=solved_tasks,
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
