import logging
from collections import Counter

from quart import Blueprint, Response, abort, jsonify, request
from quart_auth import current_user
from tortoise.expressions import Q

from wykoj.models import Task, User

client_side_api_blueprint = Blueprint("client_side", __name__)
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


@client_side_api_blueprint.route("/user/<string:username>/submission_languages")
async def user_submission_languages(username: str) -> Response:
    """JSON API endpoint for distribution of languages used in user submissions."""
    # Not much point in excluding submissions to non-public tasks
    user = await User.filter(username__iexact=username).first()
    if not user:
        abort(404)
    submissions = await user.submissions.all().only("language")
    languages = Counter([submission.language for submission in submissions])
    if len(languages) > 10:
        data = languages.most_common(9)
        data.append(("Other", sum(languages.values()) - sum(dict(data).values())))
    else:
        data = languages.most_common()
    languages, occurrences = list(zip(*data))
    return jsonify(languages=languages, occurrences=occurrences)
