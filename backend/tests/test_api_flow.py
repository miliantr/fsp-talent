"""The full demo scenario through the HTTP API, plus privacy and permission checks."""

from tests.conftest import answer_all, auth, register


def test_full_reverse_matching_flow(client, db):
    # ---------------- candidate: register, survey, profile
    ct = register(client, "flow.candidate@example.com", "candidate", first_name="Иван", last_name="Петров")
    r = client.get("/api/candidate/fsp", headers=auth(ct))
    assert r.status_code == 200 and r.json()["linked"] is False
    assert r.json()["summary"]["available"] is False  # no FSP history is a normal state

    r = client.put("/api/candidate/profile", headers=auth(ct), json={
        "specialization_id": "backend", "declared_grade_id": "middle", "city": "Москва",
        "phone": "+79990001122", "telegram": "@ivan_dev", "headline": "Python backend",
        "about": "Пишу backend на Python и FastAPI, люблю PostgreSQL и аккуратные API." * 2,
        "experience_years": 3, "expected_salary": 200000, "work_format": "remote",
        "skills": [{"slug": "python", "level": 4, "years": 3}, {"slug": "fastapi", "level": 4, "years": 2},
                   {"slug": "postgresql", "level": 4, "years": 3}, {"slug": "docker", "level": 3, "years": 2}],
    })
    assert r.status_code == 200, r.text

    # ---------------- testing: start, cannot start twice, answer, finish
    r = client.post("/api/candidate/testing/start", headers=auth(ct),
                    json={"specialization_id": "backend", "target_grade": "middle"})
    assert r.status_code == 201, r.text
    attempt = r.json()
    assert attempt["total"] == 20 and all("correct" not in i for i in attempt["items"])
    r = client.post("/api/candidate/testing/start", headers=auth(ct),
                    json={"specialization_id": "backend", "target_grade": "junior"})
    assert r.status_code == 409  # one active attempt

    choice_item = next(i for i in attempt["items"] if i["qtype"] != "numeric")
    bad = client.post("/api/candidate/testing/answer", headers=auth(ct),
                      json={"attempt_id": attempt["id"], "item_id": choice_item["id"], "answer": [99]})
    assert bad.status_code == 422

    answer_all(client, db, ct, attempt, correct=True)
    r = client.post("/api/candidate/testing/finish", headers=auth(ct), json={"attempt_id": attempt["id"]})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["passed"] and res["verified_grade"] == "middle" and res["category_label"] == "Backend · Middle"
    assert res["scaled_score"] >= 50 and res["competencies"]

    # retake of the same grade is under cooldown
    r = client.post("/api/candidate/testing/start", headers=auth(ct),
                    json={"specialization_id": "backend", "target_grade": "middle"})
    assert r.status_code == 409 and r.json()["code"] == "cooldown"

    # not searchable until publication consent
    r = client.put("/api/candidate/settings", headers=auth(ct), json={"consent_publication": True})
    assert r.json()["searchable"] is True
    cand_id = client.get("/api/candidate/profile", headers=auth(ct)).json()["id"]

    # ---------------- employer: company, need, ranking
    et = register(client, "flow.hr@example.com", "employer", company_name="ООО Тест")
    r = client.put("/api/employer/profile", headers=auth(et), json={"description": "Финтех", "city": "Москва"})
    assert r.status_code == 200
    need = {"title": "Backend Developer", "specialization_id": "backend", "grade_id": "middle",
            "must_skills": ["python", "fastapi", "postgresql", "docker"], "nice_skills": ["redis"],
            "salary_from": 180000, "salary_to": 250000, "work_format": "remote"}
    r = client.post("/api/employer/requirements", headers=auth(et), json={**need, "salary_to": 100000})
    assert r.status_code == 422  # salary_to < salary_from
    r = client.post("/api/employer/requirements", headers=auth(et), json=need)
    assert r.status_code == 201, r.text
    job_id = r.json()["id"]

    r = client.get(f"/api/employer/requirements/{job_id}/matches", headers=auth(et))
    assert r.status_code == 200
    data = r.json()
    me = next(i for i in data["items"] if i["candidate_id"] == cand_id)
    assert me["match"]["percent"] > 50 and me["match"]["reasons"]
    assert me["display_name"] == "Иван Петров" and "contacts" not in me  # name is visible, contacts are not
    assert data["categories"][0]["label"].startswith("Backend")

    # refining filters keeps the stored selection
    r = client.get(f"/api/employer/requirements/{job_id}/matches?grades=senior", headers=auth(et))
    assert r.json()["total"] == data["total"]

    r = client.get(f"/api/employer/candidates/{cand_id}?requirement_id={job_id}", headers=auth(et))
    detail = r.json()
    assert detail["contacts"] is None and detail["contacts_visible"] is False
    assert detail["match"]["components"]

    # ---------------- invitation (salary mandatory)
    inv = {"candidate_id": cand_id, "job_id": job_id, "position_title": "Backend Developer",
           "description": "Платёжный шлюз, команда 6 человек", "work_format": "remote",
           "contact_method": "Telegram @hr_test"}
    assert client.post("/api/employer/invitations", headers=auth(et), json=inv).status_code == 422
    r = client.post("/api/employer/invitations", headers=auth(et),
                    json={**inv, "salary_from": 200000, "salary_to": 250000})
    assert r.status_code == 201, r.text
    inv_id = r.json()["id"]
    assert r.json()["status"] == "sent" and r.json()["contacts"] is None
    dup = client.post("/api/employer/invitations", headers=auth(et),
                      json={**inv, "salary_from": 200000, "salary_to": 250000})
    assert dup.status_code == 409

    # ---------------- candidate sees salary before answering, accepts
    lst = client.get("/api/candidate/invitations", headers=auth(ct)).json()
    assert lst[0]["salary_from"] == 200000 and lst[0]["company"]["name"] == "ООО Тест"
    r = client.get(f"/api/candidate/invitations/{inv_id}", headers=auth(ct))
    assert r.json()["status"] == "viewed"
    r = client.post(f"/api/candidate/invitations/{inv_id}/accept", headers=auth(ct), json={"message": "Готов"})
    assert r.json()["status"] == "accepted"
    assert client.post(f"/api/candidate/invitations/{inv_id}/reject", headers=auth(ct), json={}).status_code == 409

    # ---------------- contacts are now disclosed to this employer only
    detail = client.get(f"/api/employer/candidates/{cand_id}", headers=auth(et)).json()
    assert detail["contacts_visible"] and detail["contacts"]["email"] == "flow.candidate@example.com"
    assert detail["display_name"] == "Иван Петров"
    hist = client.get("/api/employer/invitations", headers=auth(et)).json()
    assert hist[0]["status"] == "accepted" and hist[0]["contacts"]["telegram"] == "@ivan_dev"

    other = register(client, "flow.other@example.com", "employer", company_name="Другая компания")
    detail = client.get(f"/api/employer/candidates/{cand_id}", headers=auth(other)).json()
    assert detail["contacts"] is None

    # ---------------- role & ownership checks
    assert client.get("/api/employer/dashboard", headers=auth(ct)).status_code == 403
    assert client.get("/api/candidate/profile", headers=auth(et)).status_code == 403
    assert client.get(f"/api/employer/requirements/{job_id}", headers=auth(other)).status_code == 404
    assert client.get("/api/candidate/profile").status_code == 401


def test_failed_grade_allows_lower_grade_and_profile_is_kept(client, db):
    t = register(client, "fallback@example.com", "candidate", first_name="Анна", last_name="К")
    client.put("/api/candidate/profile", headers=auth(t),
               json={"specialization_id": "frontend", "declared_grade_id": "senior"})
    att = client.post("/api/candidate/testing/start", headers=auth(t),
                      json={"specialization_id": "frontend", "target_grade": "senior"}).json()
    answer_all(client, db, t, att, correct=False)
    res = client.post("/api/candidate/testing/finish", headers=auth(t), json={"attempt_id": att["id"]}).json()
    assert not res["passed"] and res["verified_grade"] is None
    status = client.get("/api/candidate/testing?specialization_id=frontend", headers=auth(t)).json()
    allowed = {e["grade"]: e["allowed"] for e in status["eligibility"]}
    assert allowed == {"junior": True, "middle": True, "senior": False}
    assert client.get("/api/candidate/profile", headers=auth(t)).status_code == 200


def test_attempt_of_another_candidate_is_not_accessible(client):
    a = register(client, "owner@example.com", "candidate")
    b = register(client, "intruder@example.com", "candidate")
    client.put("/api/candidate/profile", headers=auth(a),
               json={"specialization_id": "devops", "declared_grade_id": "junior"})
    att = client.post("/api/candidate/testing/start", headers=auth(a),
                      json={"specialization_id": "devops", "target_grade": "junior"}).json()
    assert client.get(f"/api/candidate/testing/attempts/{att['id']}", headers=auth(b)).status_code == 404


def test_login_requires_verified_email(client):
    r = client.post("/api/auth/register", json={"email": "noverify@example.com", "password": "secret123",
                                                "role": "candidate", "consent_processing": True})
    assert r.status_code == 201
    r = client.post("/api/auth/login", json={"email": "noverify@example.com", "password": "secret123"})
    assert r.status_code == 403 and r.json()["code"] == "email_not_verified"
    r = client.post("/api/auth/register", json={"email": "noconsent@example.com", "password": "secret123",
                                                "role": "candidate", "consent_processing": False})
    assert r.status_code == 422
