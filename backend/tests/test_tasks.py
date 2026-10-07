"""Regular tasks: addressed offers by the system, auto-check, pre-score and rubric review."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from app.db.base import utcnow
from app.models import CandidateProfile, ShortTask, TaskAssignment
from app.services import tasks_service
from app.services.tasks_service import check_solution, key_point_coverage
from tests.conftest import auth, employer_with_need, register, verified_candidate

APPROACH = {"specialization_id": "backend", "title": "Rate limiter",
            "description": "Спроектируйте rate limiter для публичного API", "mode": "approach",
            "key_points": ["Алгоритм token bucket", "Счётчики хранятся в Redis", "Атомарность через Lua-скрипт"]}
SOLVE = {"specialization_id": "backend", "title": "Пропускная способность",
         "description": "Запрос обрабатывается 40 мс, 8 воркеров. Сколько запросов в секунду?", "mode": "solve",
         "answer_spec": {"kind": "number", "value": 200, "tolerance": 0}}


@pytest.fixture(autouse=True)
def _only_this_tests_tasks(db):
    """The test database is shared: tasks published by other tests must not compete for offers."""
    db.execute(update(ShortTask).values(is_active=False))
    db.commit()


def _task(client, et, **body):
    r = client.post("/api/employer/tasks", headers=auth(et), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _profile(db, cid) -> CandidateProfile:
    db.expire_all()
    return db.get(CandidateProfile, cid)


# ---------------------------------------------------------------- pure checks

def test_auto_check_and_key_point_coverage():
    assert check_solution({"kind": "number", "value": 200, "tolerance": 0}, " 200 ")
    assert check_solution({"kind": "number", "value": 0.25, "tolerance": 0.01}, "0,26")
    assert not check_solution({"kind": "number", "value": 200, "tolerance": 0}, "320")
    assert check_solution({"kind": "text", "accepted": ["recall", "полнота"]}, "Полнота.")
    assert not check_solution({"kind": "text", "accepted": ["recall"]}, "accuracy")

    score, matched, missed = key_point_coverage(
        "Использую token bucket, счётчики храню в Redis с TTL.", APPROACH["key_points"])
    assert score == round(2 / 3, 3) and missed == ["Атомарность через Lua-скрипт"]
    assert key_point_coverage("что угодно", [])[0] is None


# ---------------------------------------------------------------- offers

def test_system_offers_one_addressed_task_at_a_time(client, db):
    ct, cid = verified_candidate(client, db, "offer.one@example.com")
    et, _ = employer_with_need(client, "offer.one.hr@example.com")
    first = _task(client, et, **APPROACH)
    second = _task(client, et, **{**APPROACH, "title": "Очередь заданий"})

    view = client.get("/api/candidate/tasks", headers=auth(ct)).json()
    assert len(view["offered"]) == 1 and view["verified"]
    offer = view["offered"][0]
    assert offer["source"] == "system" and offer["reasons"][0] == "Подходит к вашей категории Backend · Middle"
    assert offer["task"]["mode"] == "approach" and "key_points" not in offer["task"]  # the key stays private
    # one open offer at a time
    assert len(client.get("/api/candidate/tasks", headers=auth(ct)).json()["offered"]) == 1

    r = client.post(f"/api/candidate/tasks/offers/{offer['assignment_id']}/decline", headers=auth(ct, "en"))
    assert r.json() == {"message": "Task declined"}
    view = client.get("/api/candidate/tasks", headers=auth(ct)).json()
    assert view["offered"] == [] and view["next_offer_at"] is not None  # the next one comes after the interval

    later = tasks_service.offer_due(db, _profile(db, cid), utcnow() + timedelta(days=8))
    assert later is not None and later.task_id in {first["id"], second["id"]} - {offer["task"]["id"]}


def test_task_linked_to_a_requirement_goes_to_candidates_the_employer_considers(client, db):
    ct, cid = verified_candidate(client, db, "offer.linked@example.com")
    et, job = employer_with_need(client, "offer.linked.hr@example.com")
    client.get(f"/api/employer/requirements/{job}/matches", headers=auth(et))  # the candidate is in the ranking
    _task(client, et, **APPROACH)
    linked = _task(client, et, **{**APPROACH, "title": "Идемпотентность", "job_id": job, "competency_id": "be_api"})
    offer = client.get("/api/candidate/tasks", headers=auth(ct)).json()["offered"][0]
    assert offer["task"]["id"] == linked["id"]
    assert offer["task"]["requirement_title"] == "Backend Developer"
    assert any("рассматривает вас" in r for r in offer["reasons"])


def test_offer_expires_after_the_time_limit(client, db):
    ct, cid = verified_candidate(client, db, "offer.expire@example.com")
    et, _ = employer_with_need(client, "offer.expire.hr@example.com")
    task = _task(client, et, **{**APPROACH, "time_limit_days": 3})
    a = tasks_service.offer_due(db, _profile(db, cid), utcnow() - timedelta(days=5))
    assert a is not None and a.task_id == task["id"]
    r = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct, "en"),
                    json={"answer": "Token bucket в Redis с атомарным Lua-скриптом"})
    assert r.status_code == 409 and r.json()["code"] == "task_expired"
    db.expire_all()
    assert db.get(TaskAssignment, a.id).status == "expired"


def test_employer_can_offer_a_task_personally(client, db):
    ct, cid = verified_candidate(client, db, "offer.personal@example.com")
    et, _ = employer_with_need(client, "offer.personal.hr@example.com")
    task = _task(client, et, **{**APPROACH, "audience": "category"})
    r = client.post(f"/api/employer/tasks/{task['id']}/offer", headers=auth(et, "en"), json={"candidate_id": cid})
    assert r.json() == {"message": "The task has been offered to the candidate"}
    again = client.post(f"/api/employer/tasks/{task['id']}/offer", headers=auth(et), json={"candidate_id": cid})
    assert again.status_code == 409
    offer = client.get("/api/candidate/tasks", headers=auth(ct)).json()["offered"][0]
    assert offer["source"] == "employer" and offer["reasons"] == ["ООО Тест предлагает задание лично вам"]


# ---------------------------------------------------------------- answers and review

def test_solve_task_is_checked_automatically_and_needs_an_offer(client, db):
    ct, cid = verified_candidate(client, db, "solve.task@example.com")
    et, _ = employer_with_need(client, "solve.task.hr@example.com")
    task = _task(client, et, **SOLVE)
    # an addressed task cannot be answered before the system offers it
    r = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct), json={"answer": "200"})
    assert r.status_code == 409 and r.json()["code"] == "task_not_offered"

    assert client.get("/api/candidate/tasks", headers=auth(ct)).json()["offered"][0]["task"]["answer_kind"] == "number"
    bad = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct, "en"), json={"answer": "много"})
    assert bad.status_code == 422 and bad.json()["message"] == "The answer must be a number"
    res = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct), json={"answer": "200"})
    assert res.status_code == 201
    assert res.json()["status"] == "checked" and res.json()["correct"] is True and res.json()["score"] == 100
    assert client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct),
                       json={"answer": "200"}).status_code == 409

    stats = next(x for x in client.get("/api/employer/tasks", headers=auth(et)).json() if x["id"] == task["id"])
    assert stats["stats"] == {"offered": 1, "submitted": 1, "pending_review": 0, "avg_score": 100}


def test_approach_gets_a_pre_score_and_the_employer_rubric(client, db):
    ct, cid = verified_candidate(client, db, "approach.task@example.com")
    et, job = employer_with_need(client, "approach.task.hr@example.com")
    task = _task(client, et, **{**APPROACH, "audience": "category"})
    view = client.get("/api/candidate/tasks", headers=auth(ct)).json()
    assert task["id"] in {c["id"] for c in view["challenges"]}

    short = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct, "en"), json={"answer": "bucket"})
    assert short.status_code == 422
    res = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct),
                      json={"answer": "Алгоритм token bucket: счётчики храню в Redis, ключ на клиента и TTL."}).json()
    assert res["status"] == "pending_review" and res["score"] is None and "auto_detail" not in res

    sub = client.get(f"/api/employer/tasks/{task['id']}/submissions", headers=auth(et)).json()[0]
    assert sub["auto_score"] == round(2 / 3, 3) and sub["auto_detail"]["missed"] == ["Атомарность через Lua-скрипт"]
    bad = client.post(f"/api/employer/submissions/{sub['id']}/review", headers=auth(et),
                      json={"rubric": {"correctness": 3, "completeness": 1, "reasoning": 1}})
    assert bad.status_code == 422
    r = client.post(f"/api/employer/submissions/{sub['id']}/review", headers=auth(et, "en"), json={
        "rubric": {"correctness": 2, "completeness": 1, "reasoning": 1}, "comment": "Не хватает атомарности"})
    assert r.json() == {"message": "Rating saved"}

    mine = client.get("/api/candidate/tasks", headers=auth(ct)).json()["history"][0]
    assert mine["status"] == "reviewed" and mine["score"] == 67 and mine["reviewer_comment"] == "Не хватает атомарности"
    assert mine["rubric"] == {"correctness": 2, "completeness": 1, "reasoning": 1}

    # a fresh signal: on the shortlist card and in the explanation
    m = client.get(f"/api/employer/requirements/{job}/matches?refresh=true", headers=auth(et)).json()
    card = next(i for i in m["items"] if i["candidate_id"] == cid)
    assert card["tasks"]["done"] == 1 and card["tasks"]["avg_score"] == 67
    assert any(r["text"].startswith("Свежий сигнал сегодня: задание «Rate limiter»") for r in card["match"]["reasons"])


def test_challenge_is_for_its_category_and_the_key_is_validated(client, db):
    ct, _ = verified_candidate(client, db, "challenge.other@example.com")
    et, _ = employer_with_need(client, "challenge.other.hr@example.com")
    task = _task(client, et, **{**APPROACH, "specialization_id": "frontend", "audience": "category"})
    assert task["id"] not in {c["id"] for c in client.get("/api/candidate/tasks", headers=auth(ct)).json()["challenges"]}
    r = client.post(f"/api/candidate/tasks/{task['id']}/submit", headers=auth(ct),
                    json={"answer": "Виртуализация списка и мемоизация карточек"})
    assert r.status_code == 409

    r = client.post("/api/employer/tasks", headers=auth(et, "en"), json={**SOLVE, "answer_spec": None})
    assert r.status_code == 422 and r.json()["message"].startswith("An auto-checked task needs the correct answer")
    r = client.post("/api/employer/tasks", headers=auth(et, "en"), json={**APPROACH, "competency_id": "fe_js"})
    assert r.status_code == 422


def test_unverified_candidate_gets_no_offers(client):
    token = register(client, "no.category.tasks@example.com", "candidate")
    view = client.get("/api/candidate/tasks", headers=auth(token)).json()
    assert view["offered"] == [] and view["challenges"] == [] and view["verified"] is False
