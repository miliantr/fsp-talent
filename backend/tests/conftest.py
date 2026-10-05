import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.as_posix()}"
os.environ["EMAIL_DEV_EXPOSE_CODE"] = "true"
os.environ["SMTP_HOST"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.reference import seed_reference  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference(db)
    yield
    engine.dispose()


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture
def client():
    return TestClient(app)


def register(client: TestClient, email: str, role: str, **extra) -> str:
    r = client.post("/api/auth/register", json={"email": email, "password": "secret123", "role": role,
                                                "consent_processing": True, **extra})
    assert r.status_code == 201, r.text
    code = r.json()["dev_code"]
    r = client.post("/api/auth/verify-email", json={"email": email, "code": code})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
