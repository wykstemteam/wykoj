from quart import Blueprint

from wykoj.blueprints.api.client import client_side_api_blueprint
from wykoj.blueprints.api.judge import judge_api_blueprint

api = Blueprint("api", __name__)
api.register_blueprint(client_side_api_blueprint)
api.register_blueprint(judge_api_blueprint)
