from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Configure an isolated environment BEFORE the application is imported.
_SESSION_DIR = Path(tempfile.mkdtemp(prefix="docpredict-tests-"))
os.environ["DOCPREDICT_DATA_DIR"] = str(_SESSION_DIR)
os.environ["DOCPREDICT_TEMP_DIR"] = str(_SESSION_DIR / "tmp")
os.environ["DOCPREDICT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-0123456789"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import database  # noqa: E402
from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.security import login_throttle  # noqa: E402

PASSWORD = "Sup3rSecret!"


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "test.db"
    database.configure(f"sqlite:///{path.as_posix()}")
    database.init_db()
    login_throttle.reset()
    yield path
    database.engine.dispose()


@pytest.fixture()
def client(db_path: Path) -> TestClient:
    with TestClient(app) as c:
        yield c


def register(client: TestClient, email: str = "alice@example.com", name: str = "Alice Smith",
             password: str = PASSWORD) -> dict:
    res = client.post("/api/auth/register", json={"email": email, "full_name": name, "password": password})
    assert res.status_code == 201, res.text
    return res.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def alice(client: TestClient) -> dict:
    data = register(client)
    return {"token": data["access_token"], "headers": auth_headers(data["access_token"]), "user": data["user"]}


@pytest.fixture()
def bob(client: TestClient) -> dict:
    data = register(client, email="bob@example.com", name="Bob Jones")
    return {"token": data["access_token"], "headers": auth_headers(data["access_token"]), "user": data["user"]}


@pytest.fixture()
def temp_dir() -> Path:
    return settings.temp_dir
