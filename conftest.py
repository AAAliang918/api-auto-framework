import pytest
import logging
from common.config import BASE_URL, TIMEOUT, USERS
from common.request_util import RequestUtil
from pathlib import Path
def _setup_logging():
    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(log_dir / "run.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])
_setup_logging()
@pytest.fixture(scope="session")
def clients():
    pool = {user: RequestUtil(BASE_URL, TIMEOUT) for user in USERS}
    for user, client in pool.items():
        assert client.login(user, USERS[user]), f"{user} 登录失败"
    pool["guest"] = RequestUtil(BASE_URL, TIMEOUT)

    yield pool

    for client in pool.values():
        client.close()


@pytest.fixture(scope="session")
def api_client(clients):
    return clients["admin"]


@pytest.fixture(scope="session")
def token(api_client):
    return api_client.token


@pytest.fixture
def auth_headers(token):
    return {"Authorization": "Bearer " + token}
