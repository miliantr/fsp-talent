"""Business rules beyond the main scenario: privacy settings, the job board, invitation limits,
FSP ID linking, short tasks and English-language need descriptions."""

from app.services.nlp.extractor import parse_need_text
from tests.conftest import auth, employer_with_need, register, verified_candidate


def _invite(client, et, cid, job, lang=None, **extra):
    body = {"candidate_id": cid, "job_id": job, "position_title": "Backend Developer", "salary_from": 200_000,
            "salary_to": 250_000, "description": "Платёжный шлюз, команда 6 человек", "work_format": "remote",
            "contact_method": "Telegram @hr", **extra}
    return client.post("/api/employer/invitations", headers=auth(et, lang), json=body)


def test_privacy_settings_control_name_and_visibility(client, db):
    ct, cid = verified_candidate(client, db, "privacy@example.com", "Пётр")
    et, job = employer_with_need(client, "privacy.hr@example.com")

    # the full name is visible before contact (only contacts are closed); the last name can be hidden
    card = client.get(f"/api/employer/candidates/{cid}", headers=auth(et)).json()
    assert card["display_name"] == "Пётр Тестов" and card["contacts"] is None
    client.put("/api/candidate/settings", headers=auth(ct), json={"show_full_name": False})
    assert client.get(f"/api/employer/candidates/{cid}", headers=auth(et)).json()["display_name"] == "Пётр Т."

    # "not open to offers" removes the candidate from search and blocks invitations
    client.put("/api/candidate/settings", headers=auth(ct), json={"open_to_offers": False})
    bank = client.get("/api/employer/candidates", headers=auth(et)).json()
    assert cid not in {c["candidate_id"] for c in bank["items"]}
    r = _invite(client, et, cid, job, "en")
    assert r.status_code == 404 and r.json()["message"] == "The candidate was not found or is not accepting offers"

    # withdrawing publication consent hides the profile as well
    client.put("/api/candidate/settings", headers=auth(ct), json={"open_to_offers": True, "consent_publication": False})
    assert client.get(f"/api/employer/candidates/{cid}", headers=auth(et)).status_code == 404


def test_invitation_salary_rules_withdrawal_and_report(client, db):
    ct, cid = verified_candidate(client, db, "inv.rules@example.com", "Олег")
    et, job = employer_with_need(client, "inv.rules.hr@example.com")

    too_wide = _invite(client, et, cid, job, "en", salary_from=100_000, salary_to=400_000)
    assert too_wide.status_code == 422 and too_wide.json()["code"] == "salary_range"
    inverted = _invite(client, et, cid, job, "en", salary_from=300_000, salary_to=200_000)
    assert inverted.status_code == 422
    assert inverted.json()["message"] == "The upper bound of the range is below the lower bound"

    inv = _invite(client, et, cid, job).json()
    assert client.post(f"/api/employer/invitations/{inv['id']}/withdraw", headers=auth(et)).json()["status"] == \
        "withdrawn"
    again = client.post(f"/api/employer/invitations/{inv['id']}/withdraw", headers=auth(et, "en"))
    assert again.status_code == 409 and again.json()["message"] == "Only an active invitation can be withdrawn"

    # a withdrawn invitation does not block a new one; the candidate can report it
    inv2 = _invite(client, et, cid, job).json()
    r = client.post(f"/api/candidate/invitations/{inv2['id']}/report", headers=auth(ct, "en"),
                    json={"reason": "spam"})
    assert r.status_code == 200 and r.json()["candidate_message"] == "Complaint: spam"


def test_application_to_a_vacancy_discloses_contacts_to_that_employer_only(client, db):
    ct, cid = verified_candidate(client, db, "applicant@example.com", "Вера")
    et, job = employer_with_need(client, "jobboard.hr@example.com", is_public=True, title="Python Developer")
    other, _ = employer_with_need(client, "jobboard.other@example.com")

    jobs = client.get("/api/jobs", headers=auth(ct)).json()
    listed = next(j for j in jobs if j["id"] == job)
    assert listed["match_percent"] is not None and listed["salary_from"] == 180_000

    r = client.post("/api/applications", headers=auth(ct), json={"job_id": job, "cover_letter": "Интересно"})
    assert r.status_code == 201, r.text
    dup = client.post("/api/applications", headers=auth(ct, "en"), json={"job_id": job})
    assert dup.status_code == 409 and dup.json()["message"] == "You have already applied to this vacancy"

    apps = client.get("/api/employer/applications", headers=auth(et)).json()
    mine = next(a for a in apps if a["candidate"]["candidate_id"] == cid)
    assert mine["contacts"]["email"] == "applicant@example.com"
    assert client.get(f"/api/employer/candidates/{cid}", headers=auth(et)).json()["contacts_visible"]
    assert client.get(f"/api/employer/candidates/{cid}", headers=auth(other)).json()["contacts"] is None

    r = client.post(f"/api/employer/applications/{mine['id']}/status", headers=auth(et, "en"),
                    json={"status": "accepted"})
    assert r.json() == {"message": "Status updated"}
    assert client.get("/api/applications", headers=auth(ct)).json()[0]["status"] == "accepted"


def test_fsp_id_link_requires_a_code_and_cannot_be_shared(client):
    a = register(client, "fsp.owner@example.com", "candidate")
    b = register(client, "fsp.other@example.com", "candidate")
    assert client.post("/api/candidate/fsp/link", headers=auth(a, "en"), json={"fsp_id": "FSP-404404"}).json()[
        "message"] == "No participant with this FSP ID in the registry"

    pending = client.post("/api/candidate/fsp/link", headers=auth(a), json={"fsp_id": "FSP-200002"}).json()
    assert pending["status"] == "confirmation_required" and pending["dev_code"]
    wrong = "000000" if pending["dev_code"] != "000000" else "111111"
    r = client.post("/api/candidate/fsp/confirm", headers=auth(a, "en"), json={"code": wrong})
    assert r.status_code == 422 and r.json()["message"] == "Invalid code"
    r = client.post("/api/candidate/fsp/confirm", headers=auth(a, "en"), json={"code": pending["dev_code"]})
    assert r.status_code == 200 and r.json()["linked"] and r.json()["summary"]["available"]
    levels = {x["level_name"] for x in r.json()["profile"]["achievements"]}
    assert levels and levels <= {"international", "national (all-Russian)", "interregional", "regional"}

    taken = client.post("/api/candidate/fsp/link", headers=auth(b, "en"), json={"fsp_id": "FSP-200002"})
    assert taken.status_code == 409 and taken.json()["code"] == "fsp_taken"


def test_short_task_submission_and_review(client, db):
    ct, _ = verified_candidate(client, db, "tasker@example.com", "Ольга")
    et, _ = employer_with_need(client, "tasks.hr@example.com")
    task = client.post("/api/employer/tasks", headers=auth(et), json={
        "specialization_id": "backend", "title": "Rate limiter", "description": "Спроектируйте rate limiter для API"})
    assert task.status_code == 201, task.text
    tid = task.json()["id"]
    assert tid in {t["id"] for t in client.get("/api/candidate/tasks", headers=auth(ct)).json()}

    short = client.post(f"/api/candidate/tasks/{tid}/submit", headers=auth(ct, "en"), json={"answer": "token bucket"})
    assert short.status_code == 422 and short.json()["message"] == "Field “Answer”: at least 20 characters"
    ok = client.post(f"/api/candidate/tasks/{tid}/submit", headers=auth(ct, "en"),
                     json={"answer": "Token bucket в Redis: ключ на клиента, атомарный Lua-скрипт, TTL."})
    assert ok.json() == {"message": "Solution submitted"}
    assert client.post(f"/api/candidate/tasks/{tid}/submit", headers=auth(ct),
                       json={"answer": "Повторная отправка того же решения"}).status_code == 409

    sub = client.get(f"/api/employer/tasks/{tid}/submissions", headers=auth(et)).json()[0]
    assert client.post(f"/api/employer/submissions/{sub['id']}/review", headers=auth(et),
                       json={"rating": 6}).status_code == 422
    r = client.post(f"/api/employer/submissions/{sub['id']}/review", headers=auth(et, "en"), json={"rating": 5})
    assert r.json() == {"message": "Rating saved"}
    assert client.get("/api/employer/tasks/999999/submissions", headers=auth(et, "en")).json()["message"] == \
        "Task not found"


def test_english_need_description_is_parsed():
    p = parse_need_text("Looking for a Middle Python backend developer: FastAPI, PostgreSQL, Docker; "
                        "Redis is a plus. Salary 190-260k, remote, 2+ years of experience.")
    assert p.specialization == "backend" and p.grade == "middle" and p.work_format == "remote"
    assert (p.salary_from, p.salary_to) == (190_000, 260_000) and p.experience_years == 2
    assert p.nice_skills == ["redis"] and p.skills[:4] == ["python", "fastapi", "postgresql", "docker"]
    assert parse_need_text("Go and Kubernetes. Nice to have: Kafka, gRPC").nice_skills == ["kafka", "grpc"]
    assert parse_need_text("Senior frontend, React; preferably Next.js").nice_skills == ["nextjs"]
    assert (parse_need_text("from 150 to 200k").salary_from, parse_need_text("from 150 to 200k").salary_to) == \
        (150_000, 200_000)
