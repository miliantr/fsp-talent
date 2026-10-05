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


def auth(token: str, lang: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if lang:
        headers["Accept-Language"] = lang
    return headers


def answer_all(client: TestClient, db, token: str, attempt: dict, correct: bool = True) -> None:
    """Answers every item of an attempt using the stored key (right or deliberately wrong)."""
    from app.models import TestItem

    for item in attempt["items"]:
        row = db.get(TestItem, item["id"])
        db.refresh(row)
        if correct:
            ans = row.correct
        elif row.qtype == "numeric":
            ans = [float(row.correct[0]) + 7]
        else:
            ans = [next(i for i in range(len(row.options)) if i not in row.correct)]
        r = client.post("/api/candidate/testing/answer", headers=auth(token),
                        json={"attempt_id": attempt["id"], "item_id": item["id"], "answer": ans})
        assert r.status_code == 200, r.text


def verified_candidate(client: TestClient, db, email: str, first_name: str = "Тест", *,
                       skills: list[str] = ("python", "fastapi", "postgresql", "docker"),
                       salary: int = 200_000, publish: bool = True) -> tuple[str, int]:
    """A candidate with a verified Backend · Middle category (and publication consent)."""
    token = register(client, email, "candidate", first_name=first_name, last_name="Тестов")
    r = client.put("/api/candidate/profile", headers=auth(token), json={
        "specialization_id": "backend", "declared_grade_id": "middle", "city": "Москва",
        "phone": "+79990001122", "telegram": "@test_dev", "expected_salary": salary, "work_format": "remote",
        "experience_years": 3, "skills": [{"slug": s, "level": 4, "years": 2} for s in skills]})
    assert r.status_code == 200, r.text
    att = client.post("/api/candidate/testing/start", headers=auth(token),
                      json={"specialization_id": "backend", "target_grade": "middle"}).json()
    answer_all(client, db, token, att)
    res = client.post("/api/candidate/testing/finish", headers=auth(token), json={"attempt_id": att["id"]})
    assert res.json()["passed"], res.text
    if publish:
        client.put("/api/candidate/settings", headers=auth(token), json={"consent_publication": True})
    return token, client.get("/api/candidate/profile", headers=auth(token)).json()["id"]


def employer_with_need(client: TestClient, email: str, **need) -> tuple[str, int]:
    token = register(client, email, "employer", company_name="ООО Тест")
    client.put("/api/employer/profile", headers=auth(token), json={"description": "Финтех", "city": "Москва"})
    body = {"title": "Backend Developer", "specialization_id": "backend", "grade_id": "middle",
            "must_skills": ["python", "fastapi", "postgresql"], "nice_skills": ["redis"],
            "salary_from": 180_000, "salary_to": 250_000, "work_format": "remote", **need}
    r = client.post("/api/employer/requirements", headers=auth(token), json=body)
    assert r.status_code == 201, r.text
    return token, r.json()["id"]
