"""Secondary scenario: public vacancies and candidate-initiated applications."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.base import utcnow
from app.i18n import t
from app.models import Application, ApplicationStatus, CandidateProfile, EmployerProfile, Job
from app.repositories.reference import skill_graph
from app.services import fsp_service, presenters, privacy
from app.services.matching import engine
from app.services.matching import service as matching


def public_jobs(db: Session, candidate: CandidateProfile | None = None, specialization: str | None = None,
                grade: str | None = None, q: str | None = None) -> list[dict]:
    query = select(Job).where(Job.is_public.is_(True), Job.status == "active")
    if specialization:
        query = query.where(Job.specialization_id == specialization)
    if grade:
        query = query.where(Job.grade_id == grade)
    jobs = list(db.scalars(query.order_by(Job.created_at.desc())))
    if q:
        ql = q.lower()
        jobs = [j for j in jobs if ql in j.title.lower() or ql in j.description.lower()
                or ql in (j.employer.company_name or "").lower()]
    applied = {}
    feats = None
    if candidate:
        applied = {a.job_id: a.status for a in db.scalars(select(Application).where(
            Application.candidate_id == candidate.id))}
        if candidate.is_verified:
            feats = matching.candidate_features(candidate)
    out = []
    graph = skill_graph()
    for j in jobs:
        d = presenters.job(j)
        d["application_status"] = applied.get(j.id)
        d["match_percent"] = engine.score_candidate(feats, matching.job_features(j), graph).percent \
            if feats else None
        out.append(d)
    if feats:  # reverse matching: the candidate sees the most relevant vacancies first
        out.sort(key=lambda d: -(d["match_percent"] or 0))
    return out


def get_public(db: Session, job_id: int) -> Job:
    j = db.get(Job, job_id)
    if not j or not j.is_public or j.status != "active":
        raise NotFound(t("error.vacancy_not_found"))
    return j


def apply(db: Session, candidate: CandidateProfile, job_id: int, cover_letter: str) -> Application:
    job = get_public(db, job_id)
    if not candidate.first_name:
        raise ValidationFailed(t("error.profile_required_apply"))
    if db.scalar(select(Application.id).where(Application.job_id == job.id,
                                              Application.candidate_id == candidate.id)):
        raise Conflict(t("error.duplicate_application"), code="duplicate_application")
    score = None
    if candidate.is_verified:
        score = engine.score_candidate(matching.candidate_features(candidate), matching.job_features(job),
                                       skill_graph()).score
    app = Application(job_id=job.id, candidate_id=candidate.id, cover_letter=cover_letter.strip(),
                      match_score=score)
    db.add(app)
    privacy.log_disclosure(db, job.employer_id, candidate.id, "application")
    candidate.last_active_at = utcnow()
    db.commit()
    db.refresh(app)
    return app


def my_applications(db: Session, candidate: CandidateProfile) -> list[dict]:
    apps = db.scalars(select(Application).where(Application.candidate_id == candidate.id)
                      .order_by(Application.created_at.desc()))
    return [{"id": a.id, "status": a.status, "created_at": a.created_at, "updated_at": a.updated_at,
             "cover_letter": a.cover_letter, "match_percent": round(a.match_score * 100) if a.match_score else None,
             "job": presenters.job(a.job)} for a in apps]


def employer_applications(db: Session, employer: EmployerProfile, job_id: int | None = None) -> list[dict]:
    q = select(Application).join(Job).where(Job.employer_id == employer.id)
    if job_id:
        q = q.where(Application.job_id == job_id)
    graph = skill_graph()
    out = []
    for a in db.scalars(q.order_by(Application.created_at.desc())):
        c = a.candidate
        fsp = fsp_service.summary_for(c, a.job.specialization_id)
        out.append({
            "id": a.id, "status": a.status, "created_at": a.created_at, "cover_letter": a.cover_letter,
            "match_percent": round(a.match_score * 100) if a.match_score else None,
            "job": {"id": a.job.id, "title": a.job.title},
            "candidate": presenters.candidate_card(c, graph, fsp, contacts_visible=True),
            "contacts": privacy.contacts(c),  # the candidate applied himself -> contacts are disclosed
        })
    return out


def set_application_status(db: Session, employer: EmployerProfile, app_id: int, status: str) -> Application:
    if status not in ApplicationStatus.ALL:
        raise ValidationFailed(t("error.unknown_status"))
    a = db.get(Application, app_id)
    if not a or a.job.employer_id != employer.id:
        raise NotFound(t("error.application_not_found"))
    a.status = status
    a.updated_at = utcnow()
    db.commit()
    return a
