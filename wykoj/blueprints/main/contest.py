import asyncio
from datetime import timedelta
from statistics import mean, median, pstdev
from typing import Optional

from quart import Blueprint, Response, abort, flash, g, redirect, render_template, request, url_for
from quart_auth import current_user

from wykoj.api import TestCaseAPI
from wykoj.blueprints.utils.access import contest_redirect
from wykoj.blueprints.utils.misc import get_page, get_running_contest
from wykoj.blueprints.utils.pagination import Pagination
from wykoj.constants import ContestStatus
from wykoj.models import Contest, ContestParticipation, Submission

contest_blueprint = Blueprint("contest", __name__, url_prefix="/contest/<int:contest_id>")


@contest_blueprint.before_request
async def before_request() -> None:
    contest_id = request.view_args["contest_id"]
    contest = await Contest.filter(id=contest_id).prefetch_related("tasks").first()
    if not contest:
        abort(404)

    if request.endpoint in ("main.contest.submissions_page", "main.contest.results"):
        # All contest tasks must be public for these endpoints
        # to be accessible by for non-admin non-contestants
        if not (
            contest.status == ContestStatus.ONGOING and
            (current_user.is_admin or await contest.is_contestant(current_user))
            or contest.status == ContestStatus.ENDED and (
                current_user.is_admin or await contest.is_contestant(current_user)
                or all(task.is_public for task in contest.tasks)
            )
        ):
            abort(404)

    running_contest = await get_running_contest()
    if (
        running_contest and contest != running_contest and not current_user.is_admin
        and await running_contest.is_contestant(current_user)
    ):
        abort(404)

    g.show_links = (
        contest.status == ContestStatus.ONGOING and
        (current_user.is_admin or await contest.is_contestant(current_user))
        or contest.status == ContestStatus.ENDED and (
            current_user.is_admin or await contest.is_contestant(current_user)
            or all(task.is_public for task in contest.tasks)
        )
    )


@contest_blueprint.route("/")
async def contest_page(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id
                                   ).prefetch_related("tasks",
                                                      "participations__task_points__task").first()

    # Prepare scoreboard of current user
    contest_task_points = []
    first_solves = []
    contest_participation = None
    if await current_user.is_authenticated:
        contest_participation = await contest.participations.filter(
            contestant=current_user.user
        ).prefetch_related("task_points").first()
        if contest_participation:
            for task in contest.tasks:
                ctp = [ctp for ctp in contest_participation.task_points if ctp.task_id == task.id]
                contest_task_points.append(ctp[0] if ctp else None)
                first_solve = await contest.submissions.filter(
                    author=current_user.user, task=task, first_solve=True
                ).first()
                first_solves.append(first_solve.time - contest.start_time if first_solve else None)

    if contest.status in (ContestStatus.PRE_PREP, ContestStatus.PREP):
        return await render_template(
            "contest/contest.html",
            title=contest.title,
            contest=contest,
            ContestStatus=ContestStatus
        )

    show_stats = (
        contest.status == ContestStatus.ONGOING and current_user.is_admin
        or contest.status == ContestStatus.ENDED and (
            current_user.is_admin or await contest.is_contestant(current_user)
            or all(task.is_public for task in contest.tasks)
        )
    )

    # Load subtask points of each contest task
    points = []
    for task in contest.tasks:
        config = await TestCaseAPI.get_config(task.task_id)
        if not config:
            abort(451)
        points.append(config["points"] if config["batched"] else [100])

    # Calculate contest statistics
    stats = {task.task_id: {"attempts": 0, "data": []} for task in contest.tasks}
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
        stats[key]["max_cnt"] = stats[key]["data"].count(stats[key]["max"]
                                                         ) if stats[key]["attempts"] else "--"
        stats[key]["mean"] = mean(stats[key]["data"]) if stats[key]["attempts"] else "--"
        stats[key]["median"] = median(stats[key]["data"]) if stats[key]["attempts"] else "--"
        stats[key]["sd"] = pstdev(stats[key]["data"]) if stats[key]["attempts"] else "--"

    return await render_template(
        "contest/contest.html",
        title=contest.title,
        contest=contest,
        contest_participation=contest_participation,
        contest_task_points=tuple(zip(contest_task_points, points)),
        contest_tasks_count=len(contest.tasks),
        first_solves=first_solves,
        stats=stats,
        show_stats=show_stats,
        ContestStatus=ContestStatus
    )


@contest_blueprint.route("/join", methods=["POST"])
@contest_redirect
async def join(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).first()
    if not (
        contest.is_public and contest.status == ContestStatus.PRE_PREP
        and await current_user.is_authenticated and not current_user.is_admin
        and not await contest.is_contestant(current_user)
    ):
        abort(400)

    await ContestParticipation.create(contest=contest, contestant=current_user.user)
    await flash("Successfully joined.", "success")
    return redirect(url_for("main.contest.contest_page", contest_id=contest.id))


@contest_blueprint.route("/leave", methods=["POST"])
@contest_redirect
async def leave(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).first()
    if not (
        contest.is_public and contest.status == ContestStatus.PRE_PREP
        and await current_user.is_authenticated and not current_user.is_admin
        and await contest.is_contestant(current_user)
    ):
        abort(400)

    await contest.participations.filter(contestant=current_user.user).delete()
    await flash("Successfully left.", "success")
    return redirect(url_for("main.contest.contest_page", contest_id=contest.id))


@contest_blueprint.route("/submissions")
async def submissions_page(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id).prefetch_related("tasks").first()

    if current_user.is_admin:
        submissions = contest.submissions.all()
    elif contest.status == ContestStatus.ONGOING and await contest.is_contestant(current_user):
        submissions = contest.submissions.filter(author=current_user.user)
    else:
        submissions = contest.submissions.filter(task__is_public=True)
    cnt = await submissions.count()
    page = get_page()
    submissions = await submissions.offset(
        (page - 1) * 50
    ).limit(50).prefetch_related("task", "author", "contest")
    pagination = Pagination(submissions, page=page, per_page=50, total=cnt)

    return await render_template(
        "contest/contest_submissions.html",
        title=f"Submissions - {contest.title}",
        contest=contest,
        submissions=submissions,
        pagination=pagination,
        show_pagination=cnt > 50
    )


@contest_blueprint.route("/results")
async def results(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id).prefetch_related("tasks").first()

    contest_participations = await contest.participations.all().prefetch_related(
        "task_points", "contestant"
    )
    # Load all points first
    await asyncio.gather(*[cp.total_points for cp in contest_participations])

    # Points of each task of each contestant
    contest_task_points = {cp: [] for cp in contest_participations}

    # Stores first solve of each task of each contestant then timedelta taken to solve
    first_solves = {cp: [] for cp in contest_participations}
    last_submission = {}

    for i, cp in enumerate(contest_participations):
        for task in contest.tasks:
            # Find corresponding contest task points for task
            ctp = [ctp for ctp in cp.task_points if ctp.task_id == task.id]
            contest_task_points[cp].append(ctp[0] if ctp else None)

            # Cannot create task with QuerySet directly (despite awaitable) so it is wrapped in async function
            async def get_first_solve(task_id: int, contestant_id: int) -> Optional[Submission]:
                return await Submission.filter(
                    task_id=task_id, author_id=contestant_id, first_solve=True, contest=contest
                ).first()

            async def get_last_submission(contestant_id: int) -> Optional[Submission]:
                return await Submission.filter(
                    author_id=contestant_id, contest=contest
                ).order_by("-time").first()

            # Get first solve of current contestant and task later
            first_solves[cp].append(
                asyncio.create_task(
                    get_first_solve(task.id, cp.contestant_id)
                )
            )

            last_submission[cp] = asyncio.create_task(get_last_submission(cp.contestant_id))

    # For each contestant-task pair, retrieve first solve
    # and calculate timedelta taken to solve (if solve exists)
    for cp in contest_participations:
        for i in range(len(contest.tasks)):
            first_solve = await first_solves[cp][i]
            first_solves[cp][i] = first_solve.time - contest.start_time if first_solve else None

    # For each contestant, retrieve last submission
    # and save the time submitted
    for cp in contest_participations:
        submission = await last_submission[cp]
        last_submission[cp] = (
            submission.time - contest.start_time if submission
            else contest.end_time - contest.start_time + timedelta(seconds=1)
            # a "latest" submission time
        )

    # First solve of each task
    contest_first_solves = await asyncio.gather(
        *[
            task.submissions.filter(first_solve=True, contest=contest
                                    ).prefetch_related("author").order_by("id").first()
            for task in contest.tasks
        ]
    )
    # Contestants who submitted the solved each task first
    contest_first_solve_contestants = [
        first_solve.author if first_solve else None for first_solve in contest_first_solves
    ]

    # Sort contest participations by points, last submission time, then username
    cp_sort_key = {
        cp: (- await cp.total_points, last_submission[cp], cp.contestant.username)
        for cp in contest_participations
    }
    contest_participations.sort(key=cp_sort_key.__getitem__)

    ranked_cp = []  # Contest participations with ranks

    for i in range(len(contest_participations)):
        ranked_cp.append((i + 1, contest_participations[i]))

    return await render_template(
        "contest/contest_results.html",
        title=f"Results - {contest.title}",
        contest=contest,
        contest_participations=contest_participations,
        # ranked_cp=ranked_cp,
        contest_task_points=contest_task_points,
        first_solves=first_solves,
        contest_tasks_count=len(contest.tasks),
        contest_first_solve_contestants=contest_first_solve_contestants
    )


@contest_blueprint.route("/editorial")
async def editorial(contest_id: int) -> str:
    contest = await Contest.filter(id=contest_id).first()
    if not contest.publish_editorial:
        abort(404)

    return await render_template(
        "contest/editorial.html", title=f"Editorial - {contest.title}", contest=contest
    )
