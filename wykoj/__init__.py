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
    logger.warn("coloredlogs unavailable")

auth_manager = AuthManager()
bcrypt = Bcrypt()
rate_limiter = RateLimiter(default_limits=[RateLimit(30, timedelta(seconds=60))])

# aiohttp session initialized on startup for making requests to judge api
session: Optional[ClientSession] = None
root_path: str

def create_app(test: bool = False) -> Quart:
    app = Quart(__name__, static_url_path="/static")
    app.config.from_file(os.path.join(app.root_path, "config.json"), json.load)  # ujson

    app.config["TRAP_HTTP_EXCEPTIONS"] = True  # To set custom page for all HTTP exceptions
    app.config["JSON_SORT_KEYS"] = False

    app.config["QUART_AUTH_COOKIE_SAMESITE"] = "Lax"
    app.config["QUART_AUTH_DURATION"] = 7 * 24 * 60 * 60  # 1 week

    global root_path
    root_path = app.root_path

    # Why use a global like this instead of using current_app.root_path?
    # I'm glad you asked (though you didn't).
    # Quart follows Flask's design of contexts.
    # If you run a coroutine (asyncio.create_task()) in the background,
    # you must use @copy_current_app_context to access current_app within the coroutine.
    # Example: JudgeAPI.judge_submission being called in main.py
    # Sunny (@PunnyBunny) made a task with 195 MB of test cases.
    # Cue the fact that we have to run this web server on an EC2
    # and just have 1 GB RAM because we are poor.
    # And also because the school didn't let us host it on their servers.
    # I wonder which school it is.
    # Anyway we can't load all the test cases into memory without the server crashing,
    # so we stream the response with an asynchronous generator.
    # It calls iter_test_cases which calls get_config, both access current_app.root_path.
    # If you add @copy_current_app_context to the generator,
    # you waste 2 hours to find out it doesn't work
    # because it's only supposed to work on coroutines.

    # Snippet of copy_current_app_context:
    # >    @wraps(func)
    # >    async def wrapper(*args: Any, **kwargs: Any) -> Any:
    # >        async with app_context:
    # >            return await func(*args, **kwargs)

    # It awaits the object passed to it.
    # When an async generator is awaited, it isn't an async generator anymore.
    # IterableBody identifies it as an iterable
    # and tries to iterate over it which throws an error.
    # We store current_app.root_path in a variable on initialization
    # so we don't have to use contexts.

    # OK back to our regularly scheduled programming (pun intended)

    auth_manager.init_app(app)
    bcrypt.init_app(app)
    rate_limiter.init_app(app)

    register_tortoise(app, config=TORTOISE_CONFIG)

    from wykoj.models import UserWrapper
    auth_manager.user_class = UserWrapper

    from wykoj.blueprints import admin, api, errors, main, miscellaneous, template_filters

    app.register_blueprint(main)
    app.register_blueprint(admin)
    app.register_blueprint(api)
    app.register_blueprint(errors)
    app.register_blueprint(template_filters)
    app.register_blueprint(miscellaneous)

    return app


__all__ = ("__version__", "auth_manager", "bcrypt", "create_app")
