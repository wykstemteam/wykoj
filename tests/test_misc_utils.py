import pytest
from quart import Quart

from wykoj.blueprints.utils.misc import is_safe_url


@pytest.fixture
def app() -> Quart:
    # A bare Quart app is enough for a request context; no need to go through
    # wykoj.create_app() (which would also wire up the DB, blueprints, etc.)
    # for a function that only reads request.host_url.
    return Quart(__name__)


@pytest.mark.asyncio
async def test_relative_path_is_safe(app: Quart):
    async with app.test_request_context("/", headers={"host": "wykoj.com"}):
        assert is_safe_url("/tasks") is True


@pytest.mark.asyncio
async def test_same_origin_absolute_url_is_safe(app: Quart):
    async with app.test_request_context("/", headers={"host": "wykoj.com"}):
        assert is_safe_url("http://wykoj.com/tasks") is True


@pytest.mark.asyncio
async def test_different_host_is_unsafe(app: Quart):
    async with app.test_request_context("/", headers={"host": "wykoj.com"}):
        assert is_safe_url("http://evil.com/tasks") is False


@pytest.mark.asyncio
async def test_protocol_relative_url_is_unsafe(app: Quart):
    # //evil.com is parsed as a different netloc, guarding against this classic
    # open-redirect bypass
    async with app.test_request_context("/", headers={"host": "wykoj.com"}):
        assert is_safe_url("//evil.com/tasks") is False


@pytest.mark.asyncio
async def test_non_http_scheme_is_unsafe(app: Quart):
    async with app.test_request_context("/", headers={"host": "wykoj.com"}):
        assert is_safe_url("javascript:alert(1)") is False
