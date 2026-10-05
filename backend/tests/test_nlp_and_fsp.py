from datetime import date

from app.services.fsp.registry import MockFSPRegistry
from app.services.fsp.scoring import summarize
from app.services.nlp.extractor import parse_need_text, parse_resume_text


def test_need_text_is_parsed_into_structured_requirement():
    p = parse_need_text("Ищем Middle бэкенд-разработчика: Python, FastAPI, Postgres, Docker. "
                        "Вилка 180 000 – 250 000 ₽, удалёнка, опыт от 2 лет.")
    assert p.specialization == "backend" and p.grade == "middle"
    assert {"python", "fastapi", "postgresql", "docker"} <= set(p.skills)
    assert (p.salary_from, p.salary_to) == (180_000, 250_000)
    assert p.work_format == "remote" and p.experience_years == 2


def test_salary_range_with_unit_only_after_upper_bound():
    for text in ("Вилка 190–260 тыс., гибрид", "от 190 до 260 тыс", "190k-260k"):
        p = parse_need_text(text)
        assert (p.salary_from, p.salary_to) == (190_000, 260_000), text


def test_nice_to_have_skills_are_separated_from_must_have():
    p = parse_need_text("Python, FastAPI, PostgreSQL, Docker, желательно Redis. Kafka будет плюсом")
    assert p.nice_skills == ["redis", "kafka"]
    assert p.skills[:4] == ["python", "fastapi", "postgresql", "docker"]  # must-have first
    assert parse_need_text("Go, Kubernetes; знание Kafka приветствуется").nice_skills == ["kafka"]


def test_phone_number_is_not_read_as_salary():
    p = parse_resume_text("Олимпиев Олег\n+7 916 555-12-34\nОжидания от 220 000 ₽")
    assert p.salary_from == 220_000 and p.phone == "+79165551234"


def test_resume_text_contacts_and_skills():
    text = "Петров Иван\nivan@example.com, +7 999 123-45-67, t.me/ivan_dev\nSenior Frontend: React, TypeScript, Next.js"
    p = parse_resume_text(text)
    assert p.first_name == "Иван" and p.last_name == "Петров"
    assert p.email == "ivan@example.com" and p.phone == "+79991234567" and p.telegram == "@ivan_dev"
    assert p.grade == "senior" and {"react", "typescript", "nextjs"} <= set(p.skills)


def test_fsp_summary_without_history():
    s = summarize([], "backend", date(2026, 10, 1))
    assert s.available is False and s.count == 0


def test_mock_registry_contract(tmp_path):
    f = tmp_path / "r.json"
    f.write_text('{"participants": [{"fsp_id": "FSP-1", "full_name": "Тест", "email": "a@b.c", "region": null,'
                 '"sport_rank": null, "achievements": [{"id": "A1", "event_name": "E", "discipline": "D",'
                 '"level": "regional", "date": "2025-01-01", "place": 1, "participants_total": 10,'
                 '"team_name": null, "role": null, "score": null, "specialization_hint": null,'
                 '"certificate_url": null}]}]}', encoding="utf-8")
    reg = MockFSPRegistry(f)
    assert reg.get_participant("fsp-1").achievements[0].place == 1
    assert reg.find_by_email("A@B.C").fsp_id == "FSP-1"
    assert reg.get_participant("FSP-404") is None
