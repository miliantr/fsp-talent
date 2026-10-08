"""Places of work: profile, validation, employer view, CV parsing."""

from app.services.nlp.extractor import parse_experience, parse_resume_text
from tests.conftest import auth, employer_with_need, verified_candidate

JOBS = [
    {"company": "Студия «Пиксель»", "position": "Junior Python developer", "period_from": "2021-06",
     "period_to": "2023-01"},
    {"company": "ФинПоток", "position": "Backend-разработчик", "period_from": "2023-02", "period_to": None,
     "description": "Платёжный API"},
]


def test_places_of_work_are_saved_most_recent_first_and_shown_to_employers(client, db):
    ct, cid = verified_candidate(client, db, "jobs.history@example.com")
    r = client.put("/api/candidate/profile", headers=auth(ct), json={"experience": JOBS})
    assert r.status_code == 200, r.text
    assert [e["company"] for e in r.json()["experience"]] == ["ФинПоток", "Студия «Пиксель»"]
    assert r.json()["experience"][0] == {"company": "ФинПоток", "position": "Backend-разработчик",
                                         "period_from": "2023-02", "period_to": None, "description": "Платёжный API"}
    # other profile updates keep the list; an explicit list replaces it
    client.put("/api/candidate/profile", headers=auth(ct), json={"city": "Казань"})
    assert len(client.get("/api/candidate/profile", headers=auth(ct)).json()["experience"]) == 2

    et, job = employer_with_need(client, "jobs.history.hr@example.com")
    detail = client.get(f"/api/employer/candidates/{cid}?requirement_id={job}", headers=auth(et)).json()
    assert [e["company"] for e in detail["experience"]] == ["ФинПоток", "Студия «Пиксель»"]
    assert detail["contacts"] is None  # places of work are visible, contacts are not


def test_periods_are_validated(client, db):
    ct, _ = verified_candidate(client, db, "jobs.validate@example.com")
    bad_order = [{**JOBS[0], "period_from": "2024-01", "period_to": "2023-05"}]
    r = client.put("/api/candidate/profile", headers=auth(ct, "en"), json={"experience": bad_order})
    assert r.status_code == 422 and r.json()["message"] == \
        "Experience at “Студия «Пиксель»”: the end is earlier than the start"
    r = client.put("/api/candidate/profile", headers=auth(ct), json={"experience": [{**JOBS[0], "period_from": "2023-13"}]})
    assert r.status_code == 422
    assert client.put("/api/candidate/profile", headers=auth(ct), json={"experience": []}).json()["experience"] == []


def test_places_of_work_are_parsed_from_a_cv():
    text = ("Олимпиев Олег\nPython backend-разработчик\n"
            "2023–2026 · ООО «Платёжные решения» — backend-разработчик: REST API на FastAPI, PostgreSQL.\n"
            "03.2021 – н.в., Северный Код — Middle Python developer\n"
            "Зарплата от 220 000 – 250 000 ₽\nОпыт работы — 3 года\n")
    jobs = parse_experience(text)
    assert jobs == [
        {"company": "ООО «Платёжные решения»", "position": "backend-разработчик", "period_from": "2023",
         "period_to": "2026", "description": "REST API на FastAPI, PostgreSQL."},
        {"company": "Северный Код", "position": "Middle Python developer", "period_from": "2021-03",
         "period_to": None, "description": ""},
    ]
    assert parse_resume_text(text).experience == jobs
    assert parse_experience("2019 – present · Acme — Backend developer")[0]["period_to"] is None
