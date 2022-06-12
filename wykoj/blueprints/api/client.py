import logging
from collections import Counter

from quart import Blueprint, Response, abort, jsonify, request
from quart_auth import current_user
from tortoise.expressions import Q
from tortoise.functions import Count

from wykoj.constants import ContestStatus
from wykoj.models import Contest, Submission, Task, User

client_side_api_blueprint = Blueprint("client_side", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


@client_side_api_blueprint.route("/search")
async def search() -> Response:
    """JSON API endpoint for search results."""
    query: str = request.args.get("query", "").strip()
    if len(query) < 3 or len(query) > 50:
        return jsonify(users=[], tasks=[])

    task_query = Q(task_id__icontains=query) | Q(title__icontains=query)
    if not current_user.is_admin:
        task_query &= Q(is_public=True)
    tasks = await Task.filter(task_query).only("task_id", "title")
    tasks = [{"task_id": task.task_id, "title": task.title} for task in tasks]
    user_query = Q(username__icontains=query) | Q(name__icontains=query)
    if await current_user.is_authenticated:
        user_query |= Q(english_name__icontains=query)
    users = await User.filter(user_query).only("username", "name")
    users = [{"username": user.username, "name": user.name} for user in users]
    return jsonify(tasks=tasks, users=users)


@client_side_api_blueprint.route("/user/<string:username>")
async def user_data(username: str) -> Response:
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)

    # Distribution of languages used in user submissions to build doughnut chart
    # Not much point in excluding submissions to non-public tasks
    languages = await user.submissions.all().annotate(
        count=Count("id")
    ).group_by("language").values("language", "count")

    counter = Counter({d["language"]: d["count"] for d in languages})
    if len(counter) > 10:
        data = counter.most_common(9)
        data.append(("Other", sum(counter.values()) - sum(dict(data).values())))
    else:
        data = counter.most_common()

    languages, occurrences = list(zip(*data))
    submission_languages = {"languages": languages, "occurrences": occurrences}
    return jsonify(submission_languages=submission_languages)


@client_side_api_blueprint.route("/submission/<int:submission_id>")
async def submission_data(submission_id: int) -> Response:
    submission = await Submission.filter(id=submission_id).first()
    if not submission:
        abort(404)

    return jsonify(timestamp=submission.time.timestamp(), verdict=submission.verdict)


@client_side_api_blueprint.route("/contest/<int:contest_id>")
async def contest_data(contest_id: int) -> Response:
    contest = await Contest.filter(id=contest_id).first()
    if not contest:
        abort(404)

    data = {"status": contest.status}
    if contest.status in (ContestStatus.PRE_PREP, ContestStatus.PREP):
        data["timestamp"] = contest.start_time.timestamp()
    elif contest.status == ContestStatus.ONGOING:
        data["timestamp"] = contest.end_time.timestamp()

    return jsonify(**data)
