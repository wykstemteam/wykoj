import logging
import time
from datetime import timedelta

# quart_flask_patch required for flask-wtf
import quart_flask_patch
import ujson as json
from flask_bcrypt import Bcrypt
from quart import Quart, g, request
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
    
    # When running locally, browser will drop QUART_AUTH_COOKIE if `QUART_AUTH_COOKIE_SECURE` is set to True,
    # Issue: Login will silently fail
    app.config["QUART_AUTH_COOKIE_SECURE"] = not app.config.get("DEBUG_FLAG", False)

    app.url_map.strict_slashes = False

    # DEBUG: log every SQL statement Tortoise runs, to spot N+1 queries behind slow requests.
    logging.getLogger("tortoise.db_client").setLevel(logging.DEBUG)

    slow_request_threshold_ms = app.config.get("SLOW_REQUEST_THRESHOLD_MS", 500)

    @app.before_request
    async def _start_timer() -> None:
        g.start_time = time.perf_counter()

    @app.after_request
    async def _log_request_duration(response):
        duration_ms = (time.perf_counter() - g.start_time) * 1000
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
        if duration_ms > slow_request_threshold_ms:
            logger.warning(
                "Slow request: %s %s took %.0fms", request.method, request.path, duration_ms
            )
        return response

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
