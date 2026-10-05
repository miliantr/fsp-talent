from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationFailed
from app.db.base import utcnow
from app.domain.catalog import GRADE_RANK, SPEC_NAMES
from app.models import (
    Application,
    EmployerProfile,
    Invitation,
    InvitationStatus,
    Job,
    JobSkill,
    MatchResult,
    WorkFormat,
)
from app.repositories.reference import skill_graph, skills_by_slug
from app.services import invitation_service, presenters
from app.services.matching import service as matching
from app.services.matching.config import PRESETS
from app.services.nlp.extractor import parse_need_text

COMPANY_FIELDS = ("company_name", "industry", "description", "website", "city", "size", "contact_name",
                  "contact_email", "contact_phone", "contact_telegram")


def update_company(db: Session, e: EmployerProfile, data: dict) -> EmployerProfile:
    for k in COMPANY_FIELDS:
        if k in data and data[k] is not None:
            setattr(e, k, data[k].strip() if isinstance(data[k], str) else data[k])
    e.updated_at = utcnow()
    db.commit()
    return e


def company_view(e: EmployerProfile) -> dict:
    return {k: getattr(e, k) for k in COMPANY_FIELDS} | {"id": e.id, "email": e.user.email}


def _apply_job(db: Session, job: Job, data: dict) -> None:
    if data["specialization_id"] not in SPEC_NAMES:
        raise ValidationFailed("Неизвестная специализация")
    if data["grade_id"] not in GRADE_RANK:
        raise ValidationFailed("Неизвестный грейд")
    if data.get("work_format", "any") not in WorkFormat.ALL:
        raise ValidationFailed("Неизвестный формат работы")
    if data.get("weights_preset", "balanced") not in PRESETS:
        raise ValidationFailed("Неизвестный профиль весов")
    invitation_service.validate_salary(data["salary_from"], data["salary_to"])
    must = list(dict.fromkeys(data.get("must_skills") or []))
    nice = [s for s in dict.fromkeys(data.get("nice_skills") or []) if s not in must]
    known = skills_by_slug(db, must + nice)
    unknown = [s for s in must + nice if s not in known]
    if unknown:
        raise ValidationFailed(f"Неизвестные навыки: {', '.join(unknown)}")
    for k in ("title", "description", "team_description", "specialization_id", "grade_id", "salary_from",
              "salary_to", "work_format", "city", "min_experience_years", "weights_preset", "is_public"):
        if k in data:
            setattr(job, k, data[k])
    job.skills.clear()
    db.flush()
    for slug in must:
        job.skills.append(JobSkill(skill_id=known[slug].id, importance="must"))
    for slug in nice:
        job.skills.append(JobSkill(skill_id=known[slug].id, importance="nice"))
    job.updated_at = utcnow()


def create_job(db: Session, e: EmployerProfile, data: dict) -> Job:
    job = Job(employer_id=e.id)
    _apply_job(db, job, data)
    db.add(job)
    db.commit()
    db.refresh(job)
    matching.run(db, job)  # the ranked selection is ready immediately
    return job


def update_job(db: Session, e: EmployerProfile, job_id: int, data: dict) -> Job:
    job = matching.get_job(db, e, job_id)
    _apply_job(db, job, data)
    db.commit()
    matching.run(db, job)
    return job


def close_job(db: Session, e: EmployerProfile, job_id: int) -> None:
    job = matching.get_job(db, e, job_id)
    job.status = "closed"
    job.is_public = False
    db.commit()


def job_stats(db: Session, job: Job) -> dict:
    matched = db.scalar(select(func.count(MatchResult.id)).where(MatchResult.job_id == job.id)) or 0
    short = db.scalar(select(func.count(MatchResult.id)).where(MatchResult.job_id == job.id,
                                                               MatchResult.shortlisted.is_(True))) or 0
    inv = db.scalar(select(func.count(Invitation.id)).where(Invitation.job_id == job.id)) or 0
    acc = db.scalar(select(func.count(Invitation.id)).where(Invitation.job_id == job.id,
                                                            Invitation.status == InvitationStatus.ACCEPTED)) or 0
    apps = db.scalar(select(func.count(Application.id)).where(Application.job_id == job.id)) or 0
    top = db.scalar(select(func.max(MatchResult.score)).where(MatchResult.job_id == job.id))
    return {"matched": matched, "shortlisted": short, "invited": inv, "accepted": acc, "applications": apps,
            "top_percent": round(top * 100) if top else None}


def jobs_view(db: Session, e: EmployerProfile) -> list[dict]:
    jobs = db.scalars(select(Job).where(Job.employer_id == e.id).order_by(Job.created_at.desc()))
    return [presenters.job(j) | {"stats": job_stats(db, j)} for j in jobs]


def parse_need(text: str) -> dict:
    p = parse_need_text(text)
    graph = skill_graph()
    return {
        "specialization_id": p.specialization, "grade_id": p.grade,
        "skills": [{"slug": s, "name": graph.name(s), "importance": "nice" if s in p.nice_skills else "must"}
                   for s in p.skills[:12]],
        "salary_from": p.salary_from, "salary_to": p.salary_to, "work_format": p.work_format,
        "min_experience_years": p.experience_years,
    }


def dashboard(db: Session, e: EmployerProfile) -> dict:
    invs = invitation_service.for_employer(db, e)
    by_status: dict[str, int] = {}
    for i in invs:
        by_status[i.status] = by_status.get(i.status, 0) + 1
    jobs = jobs_view(db, e)
    responded = [i for i in invs if i.status in (InvitationStatus.ACCEPTED, InvitationStatus.REJECTED)]
    return {
        "company": company_view(e),
        "company_complete": bool(e.company_name and e.description),
        "requirements": jobs[:5],
        "requirements_total": len(jobs),
        "invitations": {"total": len(invs), "by_status": by_status,
                        "acceptance_rate": round(100 * by_status.get("accepted", 0) / len(responded))
                        if responded else None},
        "recent_responses": [presenters.invitation(i, True, invitation_service.contacts_for(db, e, i.candidate))
                             for i in sorted(responded, key=lambda i: i.responded_at or i.created_at,
                                             reverse=True)[:5]],
    }
