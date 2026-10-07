"""Behavioural integrity of a test attempt (cheating detection by how the test was taken)."""

from app.models import TestItem
from app.services.testing.integrity import ClientEvents, ItemTrace, assess, expected_seconds, fast_correct_count
from tests.conftest import auth, register


def _items(n=20, *, time_ms=40_000, correct=True, b=0.0, pasted=False):
    return [ItemTrace("single", 3, 1.2, b, 0.2, correct, time_ms, pasted) for _ in range(n)]


def test_honest_behaviour_is_ok_and_single_signals_are_tolerated():
    ok = assess(_items(), 0.3, ClientEvents(focus_lost=1, away_ms=5_000), 15 * 60_000)
    assert ok.level == "ok" and ok.points == 0
    one = assess(_items(), 0.3, ClientEvents(focus_lost=4), 15 * 60_000)
    assert one.level == "attention" and one.reasons == ["focus"]


def test_looking_answers_up_elsewhere_is_a_risk():
    r = assess(_items(pasted=True), 0.3, ClientEvents(focus_lost=9, away_ms=6 * 60_000, copies=3), 15 * 60_000)
    assert r.level == "risk"
    assert r.reasons == ["focus", "away", "paste", "copy"]
    # away share of the time actually spent: 6 min away of 20 × 40 s on items + 6 min
    assert r.signals["pastes"] == 20 and r.signals["away_share"] == round(360_000 / 1_160_000, 3)


def test_fast_correct_answers_on_items_hard_for_the_person_mark_pre_knowledge():
    hard = [ItemTrace("numeric", 4, 1.5, 1.5, 0.0, True, 4_000) for _ in range(5)]
    # the same answers are plausible for a strong candidate, suspicious for a weak one
    assert fast_correct_count(hard, theta=2.5) == 0
    assert fast_correct_count(hard, theta=-0.5) == 5
    assert assess(hard, -0.5, ClientEvents(), 10 * 60_000).reasons == ["fast_correct"]
    # «fast» is relative to the item: a quarter of the expected time
    assert abs(expected_seconds("numeric", 4) - 72) < 1e-9


def _start(client, token):
    client.put("/api/candidate/profile", headers=auth(token),
               json={"specialization_id": "backend", "declared_grade_id": "middle"})
    r = client.post("/api/candidate/testing/start", headers=auth(token),
                    json={"specialization_id": "backend", "target_grade": "middle"})
    assert r.status_code == 201, r.text
    return r.json()


def _answer_all(http, db, token, att, **extra):
    for item in att["items"]:
        row = db.get(TestItem, item["id"])
        db.refresh(row)
        r = http.post("/api/candidate/testing/answer", headers=auth(token), json={
            "attempt_id": att["id"], "item_id": item["id"], "answer": row.correct, "time_ms": 30_000, **extra})
        assert r.status_code == 200, r.text


def test_risky_behaviour_needs_a_confirmation_form(client, db):
    token = register(client, "integrity.risk@example.com", "candidate", first_name="Ян", last_name="К")
    att = _start(client, token)
    _answer_all(client, db, token, att, pasted=True, client={"focus_lost": 3, "away_ms": 60_000, "copies": 0})
    res = client.post("/api/candidate/testing/finish", headers=auth(token, "en"), json={
        "attempt_id": att["id"], "client": {"focus_lost": 11, "away_ms": 9 * 60_000, "copies": 4}}).json()
    assert res["outcome"] == "needs_confirmation" and not res["passed"] and res["verified_grade"] is None
    assert res["integrity"]["level"] == "risk"
    assert "switches away from the test tab: 11" in res["integrity"]["reasons"]
    assert "answers pasted from the clipboard: 20" in res["integrity"]["reasons"]
    # like a leak flag: one confirmation form is available at once
    status = client.get("/api/candidate/testing?specialization_id=backend", headers=auth(token)).json()
    middle = next(e for e in status["eligibility"] if e["grade"] == "middle")
    assert middle["allowed"] and middle["kind"] == "confirm"


def test_counters_cannot_be_reset_by_reloading_the_page(client, db):
    token = register(client, "integrity.reload@example.com", "candidate", first_name="Ия", last_name="М")
    att = _start(client, token)
    _answer_all(client, db, token, att, client={"focus_lost": 9, "away_ms": 0, "copies": 0})
    # after a reload the page starts counting from zero: the server keeps the maximum
    res = client.post("/api/candidate/testing/finish", headers=auth(token), json={
        "attempt_id": att["id"], "client": {"focus_lost": 0, "away_ms": 0, "copies": 0}}).json()
    assert res["integrity"]["level"] == "attention" and res["passed"]


def test_honest_attempt_passes_without_remarks(client, db):
    token = register(client, "integrity.ok@example.com", "candidate", first_name="Ая", last_name="Б")
    att = _start(client, token)
    _answer_all(client, db, token, att, client={"focus_lost": 1, "away_ms": 2_000, "copies": 0})
    res = client.post("/api/candidate/testing/finish", headers=auth(token), json={"attempt_id": att["id"]}).json()
    assert res["passed"] and res["integrity"] == {"level": "ok", "reasons": []}
