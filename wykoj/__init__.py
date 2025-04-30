import logging
from datetime import timedelta

# quart_flask_patch required for flask-wtf
import quart_flask_patch
import ujson as json
from flask_bcrypt import Bcrypt
from quart import Quart
from quart_auth import QuartAuth
from quart_rate_limiter import RateLimit, RateLimiter
from tortoise.contrib.quart import register_tortoise

from wykoj.tortoise_config import TORTOISE_CONFIG
from wykoj.version import __version__

logging.basicConfig(level="INFO", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import coloredlogs
    coloredlogs.install(level="INFO", fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
except ImportError:
    logger.info("coloredlogs unavailable")

auth_manager = QuartAuth()
bcrypt = Bcrypt()
rate_limiter = RateLimiter(default_limits=[RateLimit(150, timedelta(seconds=60))])


def create_app() -> Quart:
    app = Quart(__name__, static_url_path="/static")
    app.config.from_file("../config.json", json.load)  # ujson
    app.config["JUDGE_HOST"] = app.config["JUDGE_HOST"].rstrip("/")

    app.config["TRAP_HTTP_EXCEPTIONS"] = True  # To set custom page for all HTTP exceptions
    app.config["JSON_SORT_KEYS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000

    app.config["QUART_AUTH_COOKIE_SAMESITE"] = "Lax"
    app.config["QUART_AUTH_DURATION"] = 7 * 24 * 60 * 60  # 1 week

    app.url_map.strict_slashes = False

    auth_manager.init_app(app)
    bcrypt.init_app(app)
    rate_limiter.init_app(app)

    register_tortoise(app, config=TORTOISE_CONFIG)

    from wykoj.models import UserWrapper

    auth_manager.user_class = UserWrapper

    from wykoj.blueprints import admin, api, chess, errors, github, main, misc, template_filters

    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    app.register_blueprint(errors)
    app.register_blueprint(template_filters)
    app.register_blueprint(misc)
    app.register_blueprint(chess)
    app.register_blueprint(github)

    return app


__all__ = ("__version__", "auth_manager", "bcrypt", "create_app")
