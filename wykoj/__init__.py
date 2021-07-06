import logging
import os.path
from datetime import timedelta
from typing import Optional

import quart.flask_patch  # Required for flask-wtf
import ujson as json
from aiohttp import ClientSession
from flask_bcrypt import Bcrypt
from quart import Quart
from quart_auth import AuthManager
from quart_rate_limiter import RateLimiter, RateLimit
from tortoise.contrib.quart import register_tortoise

from wykoj.tortoise_config import TORTOISE_CONFIG
from wykoj.version import __version__

logging.basicConfig(level="INFO", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

try:
    import coloredlogs
    coloredlogs.install(level="INFO", fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
except ImportError:
    logger.warn("coloredlogs unavailable")

auth_manager = AuthManager()
bcrypt = Bcrypt()
rate_limiter = RateLimiter(default_limits=[RateLimit(30, timedelta(seconds=60))])

root_path: Optional[str] = None  # Quart contexts are problematic in background tasks. Global constants >> contexts
# Cross-module variable, import wykoj and acess with wykoj.session
session: Optional[ClientSession] = None  # aiohttp session initialized on startup for making requests to judge api


def create_app(test: bool = False) -> Quart:
    app = Quart(__name__, static_url_path="/static")
    app.config.from_file(os.path.join(app.root_path, "config.json"), json.load)  # ujson

    app.config["TRAP_HTTP_EXCEPTIONS"] = True  # To set custom page for all HTTP exceptions

    app.config["QUART_AUTH_COOKIE_SAMESITE"] = "Lax"
    app.config["QUART_AUTH_DURATION"] = 7 * 24 * 60 * 60  # 1 week

    global root_path
    root_path = app.root_path

    auth_manager.init_app(app)
    bcrypt.init_app(app)
    rate_limiter.init_app(app)

    register_tortoise(app, config=TORTOISE_CONFIG)

    from wykoj.models import UserWrapper
    auth_manager.user_class = UserWrapper

    from wykoj.blueprints import main, admin, api, errors, template_filters, miscellaneous

    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    app.register_blueprint(errors)
    app.register_blueprint(template_filters)
    app.register_blueprint(miscellaneous)

    from wykoj.blueprints.miscellaneous import init_session, close_session

    app.before_serving(init_session)
    app.after_serving(close_session)

    return app


__all__ = ("__version__", "auth_manager", "bcrypt", "create_app")
