"""Language end to end over HTTP: the same stored data is rendered for every reader in their own
language (Accept-Language), and the account remembers the chosen language."""

import re

from tests.conftest import answer_all, auth, employer_with_need, register, verified_candidate

EN = {"Accept-Language": "en-GB,en;q=0.9"}
RU = {"Accept-Language": "ru-RU,ru;q=0.9"}
CYRILLIC = re.compile(r"[А-Яа-яЁё]")


def test_errors_and_response_headers_follow_accept_language(client):
    bad_login = {"email": "nobody@example.com", "password": "secret123"}
    r = client.post("/api/auth/login", json=bad_login, headers=EN)
    assert r.status_code == 401 and r.json() == {"code": "invalid_credentials",
                                                  "message": "Invalid e-mail or password", "details": {}}
    assert r.headers["content-language"] == "en" and "Accept-Language" in r.headers["vary"]
    r = client.post("/api/auth/login", json=bad_login, headers=RU)
    assert r.json()["message"] == "Неверный e-mail или пароль" and r.headers["content-language"] == "ru"
    r = client.post("/api/auth/login", json=bad_login)  # no header -> the default language
    assert r.headers["content-language"] == "ru"
    assert client.get("/api/candidate/profile", headers=EN).json()["message"] == "Authentication required"


def test_validation_errors_name_the_field_in_the_reader_language(client):
    body = {"email": "v@example.com", "role": "candidate", "consent_processing": True}
    r = client.post("/api/auth/register", json=body, headers=EN)
    assert r.status_code == 422 and r.json()["message"] == "Field “Password” is required"
    assert client.post("/api/auth/register", json=body, headers=RU).json()["message"] == "Поле «Пароль» обязательно"
    r = client.post("/api/auth/register", json={**body, "password": "short"}, headers=EN)
    assert r.json()["message"] == "Field “Password”: at least 8 characters"
    r = client.post("/api/auth/register", json={**body, "email": "not-an-email", "password": "secret123"},
                    headers=EN)
    assert r.json()["message"] == "Invalid e-mail"
    r = client.post("/api/auth/register", json={**body, "password": "secret123", "consent_processing": False},
                    headers=EN)
    assert r.json()["message"].startswith("Consent to personal data processing is required")


def test_reference_data_is_served_in_the_request_language(client):
    en = client.get("/api/reference", headers=EN).json()
    ru = client.get("/api/reference", headers=RU).json()
    be_en = next(s for s in en["specializations"] if s["id"] == "backend")
    be_ru = next(s for s in ru["specializations"] if s["id"] == "backend")
    assert be_en["name"] == be_ru["name"] == "Backend"  # specializations and grades are proper names
    assert be_en["description"].startswith("Server-side") and be_ru["description"].startswith("Серверная")
    assert "Databases and SQL" in {c["name"] for c in be_en["competencies"]}
    assert "Базы данных и SQL" in {c["name"] for c in be_ru["competencies"]}
    assert en["component_labels"]["fsp"] == "FSP achievements" and ru["component_labels"]["fsp"] == "Достижения ФСП"
    assert {p["label"] for p in en["weight_presets"]} == {"Balanced", "Stack first", "Proven talent (test + FSP)"}
    names = [s["name"] for s in en["skills"]]
    assert "Algorithms" in names and names == sorted(names, key=str.lower)
    assert not any(CYRILLIC.search(g["description"]) for g in en["grades"])


def test_account_remembers_the_language_across_devices(client):
    r = client.post("/api/auth/register", headers=EN, json={
        "email": "lang@example.com", "password": "secret123", "role": "candidate", "consent_processing": True})
    code = r.json()["dev_code"]
    token = client.post("/api/auth/verify-email", json={"email": "lang@example.com", "code": code}).json()
    assert token["user"]["locale"] == "en"  # registered from an English UI
    tok = token["access_token"]

    r = client.put("/api/auth/me/locale", headers=auth(tok), json={"locale": "ru"})
    assert r.status_code == 200 and r.json()["locale"] == "ru"
    login = client.post("/api/auth/login", json={"email": "lang@example.com", "password": "secret123"}, headers=EN)
    assert login.json()["user"]["locale"] == "ru"  # a new device restores the saved choice
    assert client.put("/api/auth/me/locale", headers=auth(tok), json={"locale": "de"}).status_code == 422
    assert client.put("/api/auth/me/locale", json={"locale": "en"}).status_code == 401


def test_a_test_can_be_taken_in_either_language_and_switched_midway(client, db):
    tok = register(client, "bilingual@example.com", "candidate")
    client.put("/api/candidate/profile", headers=auth(tok),
               json={"specialization_id": "data_ml", "declared_grade_id": "middle"})
    att = client.post("/api/candidate/testing/start", headers=auth(tok, "en"),
                      json={"specialization_id": "data_ml", "target_grade": "middle"}).json()
    en = client.get(f"/api/candidate/testing/attempts/{att['id']}", headers=auth(tok, "en")).json()["items"]
    ru = client.get(f"/api/candidate/testing/attempts/{att['id']}", headers=auth(tok, "ru")).json()["items"]
    assert [i["id"] for i in en] == [i["id"] for i in ru]
    for a, b in zip(en, ru, strict=True):
        assert not CYRILLIC.search(a["text"] + " ".join(a["options"]) + a["competency_name"])
        assert CYRILLIC.search(b["text"] + b["competency_name"])
        assert len(a["options"]) == len(b["options"])

    # answers given in one language stay valid in the other: options keep their order
    answer_all(client, db, tok, att, correct=True)
    again = client.get(f"/api/candidate/testing/attempts/{att['id']}", headers=auth(tok, "en")).json()
    assert all(i["answer"] is not None for i in again["items"])
    res = client.post("/api/candidate/testing/finish", headers=auth(tok, "en"), json={"attempt_id": att["id"]})
    assert res.json()["passed"]
    rec_en = client.get(f"/api/candidate/testing/results/{att['id']}", headers=auth(tok, "en")).json()
    rec_ru = client.get(f"/api/candidate/testing/results/{att['id']}", headers=auth(tok, "ru")).json()
    assert rec_en["recommendation"].startswith(("Grade Middle verified", "Confident result"))
    assert rec_ru["recommendation"].startswith(("Грейд Middle подтверждён", "Уверенный результат"))
    assert not any(CYRILLIC.search(c["name"]) for c in rec_en["competencies"])

    status = client.get("/api/candidate/testing?specialization_id=data_ml", headers=auth(tok, "en")).json()
    blocked = next(e for e in status["eligibility"] if e["grade"] == "middle")
    assert not blocked["allowed"] and blocked["reason"].startswith("You can retake the Middle test after")


def test_one_ranking_snapshot_is_explained_in_each_reader_language(client, db):
    _, a = verified_candidate(client, db, "snap.a@example.com", "Анна")
    _, b = verified_candidate(client, db, "snap.b@example.com", "Борис", skills=["python", "flask"],
                              salary=400_000)
    et, job = employer_with_need(client, "snap.hr@example.com")

    def mine(lang):
        items = client.get(f"/api/employer/requirements/{job}/matches", headers=auth(et, lang)).json()["items"]
        return {i["candidate_id"]: i["match"] for i in items}

    en, ru = mine("en"), mine("ru")
    for cid in (a, b):
        assert en[cid]["percent"] == ru[cid]["percent"]  # same stored snapshot
        assert not any(CYRILLIC.search(r["text"]) for r in en[cid]["reasons"])
        assert all(CYRILLIC.search(r["text"]) for r in ru[cid]["reasons"] if r["component"] != "grade")
        assert not any(CYRILLIC.search(c["label"] + c["detail"]) for c in en[cid]["components"])
    texts_b = " ".join(r["text"] for r in en[b]["reasons"])
    assert "Related skills: Flask instead of FastAPI" in texts_b
    assert "Missing must-have skills: PostgreSQL" in texts_b and "above the range" in texts_b
    assert any(c["detail"] == "within the range" for c in en[a]["components"] if c["key"] == "salary")

    cmp_en = client.get(f"/api/employer/requirements/{job}/compare", params={"a": a, "b": b},
                        headers=auth(et, "en")).json()
    assert cmp_en["summary"].startswith("Difference +") and "Ahead on:" in cmp_en["summary"]
    cmp_ru = client.get(f"/api/employer/requirements/{job}/compare", params={"a": a, "b": b},
                        headers=auth(et, "ru")).json()
    assert cmp_ru["summary"].startswith("Разница +") and cmp_en["delta_percent"] == cmp_ru["delta_percent"]

    detail = client.get(f"/api/employer/candidates/{a}?requirement_id={job}", headers=auth(et, "en")).json()
    assert detail["match"]["reasons"] and not CYRILLIC.search(" ".join(r["text"] for r in detail["match"]["reasons"]))


def test_invitation_reasons_are_stored_once_and_read_in_each_language(client, db):
    ct, cid = verified_candidate(client, db, "inv.lang@example.com", "Ирина")
    et, job = employer_with_need(client, "inv.lang.hr@example.com")
    r = client.post("/api/employer/invitations", headers=auth(et, "ru"), json={
        "candidate_id": cid, "job_id": job, "position_title": "Backend Developer", "salary_from": 200_000,
        "salary_to": 250_000, "description": "Платёжный шлюз, команда 6 человек", "work_format": "remote",
        "contact_method": "Telegram @hr"})
    assert r.status_code == 201, r.text
    inv_en = client.get("/api/candidate/invitations", headers=auth(ct, "en")).json()[0]
    inv_ru = client.get("/api/candidate/invitations", headers=auth(ct, "ru")).json()[0]
    assert inv_en["match_reasons"] and len(inv_en["match_reasons"]) == len(inv_ru["match_reasons"])
    assert not any(CYRILLIC.search(m["text"]) for m in inv_en["match_reasons"])
    assert any("Specialization Backend matches" == m["text"] for m in inv_en["match_reasons"])
    assert any("Специализация Backend совпадает" == m["text"] for m in inv_ru["match_reasons"])
    # the candidate dashboard steps follow the language too
    steps = client.get("/api/candidate/dashboard", headers=auth(ct, "en")).json()["steps"]
    assert {s["title"] for s in steps} >= {"Verify your grade with the test", "Link your FSP ID (optional)"}
