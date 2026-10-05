"""Employer → candidate invitations: the core contact mechanic.

States: sent → viewed → accepted | rejected; sent/viewed → expired (TTL) | withdrawn (employer).
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, NotFound, TooManyRequests, ValidationFailed
from app.db.base import utcnow
from app.i18n import t
from app.models import CandidateProfile, EmployerProfile, Invitation, InvitationStatus, Job
from app.repositories import candidates as cand_repo
from app.services import privacy
from app.services.matching import service as matching

MAX_SALARY = 10_000_000
MAX_RANGE_RATIO = 3.0


def validate_salary(salary_from: int, salary_to: int) -> None:
    if salary_from <= 0 or salary_to <= 0:
        raise ValidationFailed(t("error.salary_required"), code="salary_required")
    if salary_to < salary_from:
        raise ValidationFailed(t("error.salary_range_inverted"), code="salary_range")
    if salary_to > MAX_SALARY:
        raise ValidationFailed(t("error.salary_too_large"), code="salary_range")
    if salary_to > salary_from * MAX_RANGE_RATIO:
        raise ValidationFailed(t("error.salary_too_wide"),
                               code="salary_range")


def expire_stale(db: Session, invitations: list[Invitation]) -> None:
    now = utcnow()
    changed = False
    for inv in invitations:
        if inv.status in InvitationStatus.ACTIVE and inv.expires_at < now:
            inv.status = InvitationStatus.EXPIRED
            changed = True
    if changed:
        db.commit()


def create(db: Session, employer: EmployerProfile, *, candidate_id: int, job_id: int | None,
           position_title: str, description: str, salary_from: int, salary_to: int,
           work_format: str, contact_method: str) -> Invitation:
    if not employer.company_name:
        raise ValidationFailed(t("error.company_required"), code="company_required")
    validate_salary(salary_from, salary_to)
    if not position_title.strip() or not description.strip() or not contact_method.strip():
        raise ValidationFailed(t("error.invitation_fields"))

    candidate = cand_repo.get_with_relations(db, candidate_id)
    if not candidate or not (candidate.is_searchable or privacy.has_relationship(db, employer, candidate)):
        raise NotFound(t("error.candidate_unavailable"))
    job = None
    if job_id is not None:
        job = db.get(Job, job_id)
        if not job or job.employer_id != employer.id:
            raise NotFound(t("error.requirement_not_found"))

    active = db.scalar(select(Invitation.id).where(
        Invitation.employer_id == employer.id, Invitation.candidate_id == candidate.id,
        Invitation.status.in_(InvitationStatus.ACTIVE), Invitation.expires_at > utcnow()).limit(1))
    if active:
        raise Conflict(t("error.duplicate_invitation"), code="duplicate_invitation")

    since = utcnow() - timedelta(days=1)
    sent_today = db.scalar(select(func.count(Invitation.id)).where(
        Invitation.employer_id == employer.id, Invitation.created_at >= since)) or 0
    if sent_today >= get_settings().invitations_daily_limit:
        raise TooManyRequests(t("error.invitation_limit"))

    score, reasons = None, []
    if job:
        m = matching.explain(db, job, candidate)
        if m:
            score = round(m.score, 4)
            reasons = [r.to_dict() for r in m.reasons if r.kind == "positive"][:4]

    inv = Invitation(
        employer_id=employer.id, candidate_id=candidate.id, job_id=job.id if job else None,
        position_title=position_title.strip(), description=description.strip(),
        salary_from=salary_from, salary_to=salary_to, work_format=work_format,
        contact_method=contact_method.strip(), status=InvitationStatus.SENT,
        match_score=score, match_reasons=reasons,
        expires_at=utcnow() + timedelta(days=get_settings().invitation_ttl_days),
    )
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


def for_employer(db: Session, employer: EmployerProfile, status: str | None = None) -> list[Invitation]:
    q = select(Invitation).where(Invitation.employer_id == employer.id)
    if status:
        q = q.where(Invitation.status == status)
    rows = list(db.scalars(q.order_by(Invitation.created_at.desc())))
    expire_stale(db, rows)
    return rows


def for_candidate(db: Session, candidate: CandidateProfile) -> list[Invitation]:
    rows = list(db.scalars(select(Invitation).where(Invitation.candidate_id == candidate.id)
                           .order_by(Invitation.created_at.desc())))
    expire_stale(db, rows)
    return rows


def _own(db: Session, candidate: CandidateProfile, inv_id: int) -> Invitation:
    inv = db.get(Invitation, inv_id)
    if not inv or inv.candidate_id != candidate.id:
        raise NotFound(t("error.invitation_not_found"))
    expire_stale(db, [inv])
    return inv


def open_for_candidate(db: Session, candidate: CandidateProfile, inv_id: int) -> Invitation:
    inv = _own(db, candidate, inv_id)
    if inv.status == InvitationStatus.SENT:
        inv.status = InvitationStatus.VIEWED
        inv.viewed_at = utcnow()
        candidate.last_active_at = utcnow()
        db.commit()
    return inv


def respond(db: Session, candidate: CandidateProfile, inv_id: int, accept: bool,
            message: str | None = None) -> Invitation:
    inv = _own(db, candidate, inv_id)
    if inv.status == InvitationStatus.EXPIRED:
        raise Conflict(t("error.invitation_expired"), code="invitation_expired")
    if inv.status not in InvitationStatus.ACTIVE:
        raise Conflict(t("error.invitation_closed"), code="invitation_closed")
    now = utcnow()
    inv.viewed_at = inv.viewed_at or now
    inv.status = InvitationStatus.ACCEPTED if accept else InvitationStatus.REJECTED
    inv.responded_at = now
    inv.candidate_message = (message or "").strip() or None
    candidate.last_active_at = now
    if accept:
        privacy.log_disclosure(db, inv.employer_id, candidate.id, "invitation_accepted")
    db.commit()
    return inv


def report(db: Session, candidate: CandidateProfile, inv_id: int, reason: str | None) -> Invitation:
    inv = _own(db, candidate, inv_id)
    inv.reported = True
    if inv.status in InvitationStatus.ACTIVE:
        inv.status = InvitationStatus.REJECTED
        inv.responded_at = utcnow()
        inv.candidate_message = t("invitation.report", reason=reason) if reason else t("invitation.report_plain")
    db.commit()
    return inv


def withdraw(db: Session, employer: EmployerProfile, inv_id: int) -> Invitation:
    inv = db.get(Invitation, inv_id)
    if not inv or inv.employer_id != employer.id:
        raise NotFound(t("error.invitation_not_found"))
    if inv.status not in InvitationStatus.ACTIVE:
        raise Conflict(t("error.invitation_withdraw_active"))
    inv.status = InvitationStatus.WITHDRAWN
    db.commit()
    return inv


def contacts_for(db: Session, employer: EmployerProfile, candidate: CandidateProfile) -> dict | None:
    return privacy.contacts(candidate) if privacy.contact_reason(db, employer, candidate) else None
