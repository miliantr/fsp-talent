"""Several verified categories per candidate and the status of the self-declared grade."""

from app.core.config import get_settings
from app.services.matching.engine import CandidateFeatures, SkillGraph, SkillInfo, skill_evidence
from tests.conftest import answer_all, auth, employer_with_need, register, verified_candidate


def _take(client, db, token, spec, grade, correct=True):
    att = client.post("/api/candidate/testing/start", headers=auth(token),
                      json={"specialization_id": spec, "target_grade": grade})
    assert att.status_code == 201, att.text
    answer_all(client, db, token, att.json(), correct=correct)
    return client.post("/api/candidate/testing/finish", headers=auth(token),
                       json={"attempt_id": att.json()["id"]}).json()


def test_second_specialization_adds_a_category_and_keeps_the_first(client, db):
    token, _ = verified_candidate(client, db, "two.categories@example.com")
    status = client.get("/api/candidate/testing?specialization_id=devops", headers=auth(token)).json()
    # a new specialization is a new category: no grade-change lock from the Backend category
    assert {e["grade"]: e["kind"] for e in status["eligibility"]}["junior"] == "initial"
    assert status["viewed_grade_id"] is None and status["max_categories"] == get_settings().max_categories

    res = _take(client, db, token, "devops", "junior")
    assert res["passed"] and res["category_label"] == "DevOps · Junior"

    p = client.get("/api/candidate/profile", headers=auth(token)).json()
    assert [(k["label"], k["is_primary"]) for k in p["categories"]] == [
        ("Backend · Middle", True), ("DevOps · Junior", False)]
    assert p["category"]["label"] == "Backend · Middle"  # the primary category did not change
    assert p["grade_status"]["status"] == "confirmed"
    # the lock and the fast track are kept per category
    st = client.get("/api/candidate/testing?specialization_id=devops", headers=auth(token)).json()
    assert st["viewed_grade_id"] == "junior" and st["grade_locked_until"] is not None


def test_primary_category_can_be_switched(client, db):
    token, _ = verified_candidate(client, db, "switch.primary@example.com")
    _take(client, db, token, "devops", "junior")
    r = client.put("/api/candidate/categories/devops/primary", headers=auth(token))
    assert r.status_code == 200
    p = r.json()
    assert p["category"]["label"] == "DevOps · Junior"
    assert [k["label"] for k in p["categories"]] == ["DevOps · Junior", "Backend · Middle"]
    assert client.put("/api/candidate/categories/frontend/primary", headers=auth(token)).status_code == 404


def test_number_of_categories_is_limited(client, db, monkeypatch):
    monkeypatch.setattr(get_settings(), "max_categories", 1)
    token, _ = verified_candidate(client, db, "one.category@example.com")
    status = client.get("/api/candidate/testing?specialization_id=frontend", headers=auth(token)).json()
    assert not any(e["allowed"] for e in status["eligibility"])
    assert "1" in status["eligibility"][0]["reason"]
    # the existing category can still be re-confirmed or upgraded
    status = client.get("/api/candidate/testing?specialization_id=backend", headers=auth(token)).json()
    assert any(e["allowed"] for e in status["eligibility"])


def test_requirement_sees_the_category_of_its_specialization(client, db):
    token, cid = verified_candidate(client, db, "ops.and.backend@example.com",
                                    skills=("python", "fastapi", "postgresql", "docker", "kubernetes", "terraform"))
    _take(client, db, token, "devops", "junior")
    et, devops_job = employer_with_need(client, "ops.hr@example.com", title="DevOps", specialization_id="devops",
                                        grade_id="junior", must_skills=["docker", "kubernetes"], nice_skills=[])
    m = client.get(f"/api/employer/requirements/{devops_job}/matches", headers=auth(et)).json()
    card = next(i for i in m["items"] if i["candidate_id"] == cid)
    assert card["category"]["label"] == "DevOps · Junior"
    assert {k["label"] for k in card["categories"]} == {"Backend · Middle", "DevOps · Junior"}
    assert any(c["label"] == "DevOps · Junior" for c in m["categories"])

    r = client.post("/api/employer/requirements", headers=auth(et), json={
        "title": "Python", "specialization_id": "backend", "grade_id": "middle", "must_skills": ["python"],
        "salary_from": 150_000, "salary_to": 250_000})
    m = client.get(f"/api/employer/requirements/{r.json()['id']}/matches", headers=auth(et)).json()
    card = next(i for i in m["items"] if i["candidate_id"] == cid)
    assert card["category"]["label"] == "Backend · Middle"

    bank = client.get("/api/employer/candidates?specialization_id=devops", headers=auth(et)).json()
    assert next(i for i in bank["items"] if i["candidate_id"] == cid)["category"]["label"] == "DevOps · Junior"


def test_grade_status_follows_the_self_declared_grade(client, db):
    token = register(client, "grade.status@example.com", "candidate", first_name="Ира", last_name="С")
    p = client.get("/api/candidate/profile", headers=auth(token)).json()
    assert p["grade_status"]["status"] == "no_claim"

    client.put("/api/candidate/profile", headers=auth(token),
               json={"specialization_id": "frontend", "declared_grade_id": "middle"})
    assert client.get("/api/candidate/profile", headers=auth(token)).json()["grade_status"]["status"] == "not_tested"

    res = _take(client, db, token, "frontend", "middle", correct=False)
    assert not res["passed"]
    gs = client.get("/api/candidate/profile", headers=auth(token)).json()["grade_status"]
    assert gs == {"status": "not_confirmed", "specialization_id": "frontend", "declared_grade_id": "middle",
                  "confirmed_grade_id": None}

    res = _take(client, db, token, "frontend", "junior")
    assert res["passed"]
    gs = client.get("/api/candidate/profile", headers=auth(token)).json()["grade_status"]
    assert gs["status"] == "confirmed_lower" and gs["confirmed_grade_id"] == "junior"


def test_skill_tested_in_another_category_counts_as_evidence():
    graph = SkillGraph([SkillInfo("docker", "Docker", {"backend": "be_ops", "devops": "do_containers"})])
    base = dict(id=1, specialization="backend", grade="middle", theta=0.4, scaled_score=60, confidence=0.9,
                skills={"docker": 4})
    untested, verified = skill_evidence(CandidateFeatures(**base, competency_scores={}), "docker", graph)
    tested, verified2 = skill_evidence(CandidateFeatures(**base, competency_scores={},
                                                         other_competencies={"devops": {"do_containers": 90}}),
                                       "docker", graph)
    assert not verified and verified2 and tested > untested


def test_employer_sees_an_unconfirmed_declared_grade_of_an_applicant(client, db):
    token = register(client, "applies.untested@example.com", "candidate", first_name="Гоша", last_name="Н")
    client.put("/api/candidate/profile", headers=auth(token),
               json={"specialization_id": "backend", "declared_grade_id": "senior"})
    et, job = employer_with_need(client, "declared.hr@example.com", is_public=True)
    assert client.post("/api/applications", headers=auth(token), json={"job_id": job}).status_code == 201
    card = client.get("/api/employer/applications", headers=auth(et)).json()[0]["candidate"]
    assert card["category"] is None and card["categories"] == []
    assert card["declared"] == {"label": "Backend · Senior", "specialization_id": "backend", "grade_id": "senior",
                                "confirmed": False}
