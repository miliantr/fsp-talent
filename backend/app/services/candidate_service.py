from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.db.base import utcnow
from app.domain.catalog import GRADE_RANK, SPEC_NAMES
from app.models import CandidateProfile, CandidateSkill, InvitationStatus, Skill, WorkFormat
from app.repositories.reference import skill_graph
from app.services import fsp_service, invitation_service, presenters
from app.services.nlp.extractor import parse_resume_text, pdf_to_text
from app.services.testing import service as testing_service

PROFILE_FIELDS = ("first_name", "last_name", "phone", "telegram", "city", "headline", "about",
                  "experience_years", "education", "team_roles", "soft_skills", "expected_salary",
                  "work_format", "specialization_id", "declared_grade_id")


def update_profile(db: Session, c: CandidateProfile, data: dict) -> CandidateProfile:
    if "specialization_id" in data and data["specialization_id"] and data["specialization_id"] not in SPEC_NAMES:
        raise ValidationFailed("Неизвестная специализация")
    if "declared_grade_id" in data and data["declared_grade_id"] and data["declared_grade_id"] not in GRADE_RANK:
        raise ValidationFailed("Неизвестный грейд")
    if data.get("work_format") and data["work_format"] not in WorkFormat.ALL:
        raise ValidationFailed("Неизвестный формат работы")
    for k in PROFILE_FIELDS:
        if k in data:
            setattr(c, k, data[k])
    if data.get("skills") is not None:
        set_skills(db, c, data["skills"])
    c.profile_updated_at = c.last_active_at = utcnow()
    db.commit()
    db.refresh(c)
    return c


def set_skills(db: Session, c: CandidateProfile, items: list[dict]) -> None:
    slugs = [i["slug"] for i in items]
    if len(slugs) != len(set(slugs)):
        raise ValidationFailed("Навыки не должны повторяться")
    if len(slugs) > 30:
        raise ValidationFailed("Не более 30 навыков")
    known = {s.slug: s for s in db.scalars(select(Skill).where(Skill.slug.in_(slugs)))}
    unknown = [s for s in slugs if s not in known]
    if unknown:
        raise ValidationFailed(f"Неизвестные навыки: {', '.join(unknown)}")
    c.skills.clear()
    db.flush()
    for i in items:
        c.skills.append(CandidateSkill(skill_id=known[i["slug"]].id, level=i["level"], years=i["years"]))


def update_settings(db: Session, c: CandidateProfile, data: dict) -> CandidateProfile:
    for k in ("open_to_offers", "show_full_name", "show_fsp", "show_salary"):
        if data.get(k) is not None:
            setattr(c, k, data[k])
    if data.get("consent_publication") is not None:
        c.consent_publication_at = utcnow() if data["consent_publication"] else None
    db.commit()
    return c


def completeness(c: CandidateProfile) -> dict:
    checks = [
        ("name", "Имя и фамилия", bool(c.first_name and c.last_name)),
        ("contacts", "Телефон или Telegram", bool(c.phone or c.telegram)),
        ("city", "Город", bool(c.city)),
        ("headline", "Заголовок профиля", bool(c.headline)),
        ("about", "О себе (от 50 символов)", len(c.about or "") >= 50),
        ("survey", "Опрос: специализация и грейд", bool(c.specialization_id and c.declared_grade_id)),
        ("skills", "Не менее 3 навыков", len(c.skills) >= 3),
        ("salary", "Зарплатные ожидания", bool(c.expected_salary)),
        ("test", "Пройденное тестирование", c.is_verified),
        ("publication", "Согласие на публикацию профиля", c.consent_publication_at is not None),
    ]
    done = sum(1 for _, _, ok in checks if ok)
    return {"percent": round(100 * done / len(checks)),
            "missing": [{"key": k, "title": t} for k, t, ok in checks if not ok]}


def profile_view(c: CandidateProfile) -> dict:
    graph = skill_graph()
    fsp = fsp_service.summary_for(c, None)
    return {
        "id": c.id, "email": c.user.email,
        **{k: getattr(c, k) for k in PROFILE_FIELDS},
        "team_roles": c.team_roles or [], "soft_skills": c.soft_skills or [],
        "skills": presenters.skills(c, graph),
        "category": presenters.category(c),
        "competencies": presenters.competency_list(c.competency_scores or {}),
        "completeness": completeness(c),
        "fsp": presenters.fsp_summary(fsp),
        "fsp_id": c.fsp_id,
        "settings": settings_view(c),
        "resume_filename": c.resume_filename,
        "profile_updated_at": c.profile_updated_at,
    }


def settings_view(c: CandidateProfile) -> dict:
    return {"open_to_offers": c.open_to_offers, "show_full_name": c.show_full_name, "show_fsp": c.show_fsp,
            "show_salary": c.show_salary, "consent_processing_at": c.consent_processing_at,
            "consent_publication_at": c.consent_publication_at, "searchable": c.is_searchable}


def dashboard(db: Session, c: CandidateProfile) -> dict:
    testing_service.expire_overdue(db, c)
    invs = invitation_service.for_candidate(db, c)
    results = testing_service.results(db, c)
    comp = completeness(c)
    steps = [
        {"key": "profile", "title": "Заполните профиль", "done": comp["percent"] >= 50, "link": "/candidate/profile"},
        {"key": "survey", "title": "Пройдите опрос: специализация и грейд",
         "done": bool(c.specialization_id and c.declared_grade_id), "link": "/candidate/testing"},
        {"key": "test", "title": "Подтвердите грейд тестом", "done": c.is_verified, "link": "/candidate/testing"},
        {"key": "publish", "title": "Разрешите показывать профиль работодателям",
         "done": c.consent_publication_at is not None, "link": "/candidate/settings"},
        {"key": "fsp", "title": "Привяжите ФСП ID (необязательно)", "done": bool(c.fsp_id), "link": "/candidate/fsp"},
    ]
    last = results[0] if results else None
    return {
        "profile": profile_view(c),
        "invitations": {
            "total": len(invs),
            "new": sum(1 for i in invs if i.status == InvitationStatus.SENT),
            "active": sum(1 for i in invs if i.status in InvitationStatus.ACTIVE),
            "accepted": sum(1 for i in invs if i.status == InvitationStatus.ACCEPTED),
            "latest": [presenters.invitation(i, False) for i in invs[:3]],
        },
        "last_result": {"attempt_id": last.attempt_id, "outcome": last.outcome, "scaled_score": last.scaled_score,
                        "target_grade": last.attempt.target_grade_id, "created_at": last.created_at}
        if last else None,
        "steps": steps,
        "searchable": c.is_searchable,
    }


def parse_resume(c: CandidateProfile, filename: str, data: bytes) -> dict:
    if len(data) > 5 * 1024 * 1024:
        raise ValidationFailed("Файл больше 5 МБ")
    if not data.startswith(b"%PDF"):
        raise ValidationFailed("Ожидается PDF-файл")
    try:
        text = pdf_to_text(data)
    except Exception as e:  # malformed PDFs
        raise ValidationFailed("Не удалось прочитать PDF") from e
    if len(text.strip()) < 20:
        raise ValidationFailed("В PDF не найден текст (скан?). Заполните профиль вручную.")
    p = parse_resume_text(text)
    graph = skill_graph()
    return {
        "filename": filename,
        "first_name": p.first_name, "last_name": p.last_name, "email": p.email, "phone": p.phone,
        "telegram": p.telegram, "specialization_id": p.specialization, "declared_grade_id": p.grade,
        "experience_years": p.experience_years, "work_format": p.work_format,
        "expected_salary": p.salary_from,
        "skills": [{"slug": s, "name": graph.name(s)} for s in p.skills[:20]],
        "text_preview": text[:600],
    }
