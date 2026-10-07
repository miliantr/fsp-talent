"""Visibility rules. Single place that decides what an employer may see about a candidate.

The name, the profile and the work history are visible to employers (the last name can be hidden by
the candidate). Contacts (e-mail, phone, Telegram) are disclosed to an employer only after
  * the candidate accepted this employer's invitation, or
  * the candidate applied to this employer's vacancy himself/herself.
Every disclosure is recorded in contact_access_log (152-FZ audit).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.i18n import t
from app.models import (
    Application,
    CandidateProfile,
    ContactAccessLog,
    EmployerProfile,
    Invitation,
    InvitationStatus,
    Job,
)


def contact_reason(db: Session, employer: EmployerProfile, candidate: CandidateProfile) -> str | None:
    accepted = db.scalar(select(Invitation.id).where(
        Invitation.employer_id == employer.id, Invitation.candidate_id == candidate.id,
        Invitation.status == InvitationStatus.ACCEPTED).limit(1))
    if accepted:
        return "invitation_accepted"
    applied = db.scalar(select(Application.id).join(Job, Job.id == Application.job_id).where(
        Job.employer_id == employer.id, Application.candidate_id == candidate.id).limit(1))
    if applied:
        return "application"
    return None


def has_relationship(db: Session, employer: EmployerProfile, candidate: CandidateProfile) -> bool:
    """Employer already interacted with the candidate (invitation of any status or application)."""
    inv = db.scalar(select(Invitation.id).where(Invitation.employer_id == employer.id,
                                                Invitation.candidate_id == candidate.id).limit(1))
    return bool(inv) or contact_reason(db, employer, candidate) is not None


def log_disclosure(db: Session, employer_id: int, candidate_id: int, reason: str) -> None:
    exists = db.scalar(select(ContactAccessLog.id).where(
        ContactAccessLog.employer_id == employer_id, ContactAccessLog.candidate_id == candidate_id,
        ContactAccessLog.reason == reason).limit(1))
    if not exists:
        db.add(ContactAccessLog(employer_id=employer_id, candidate_id=candidate_id, reason=reason))


def display_name(c: CandidateProfile, contacts_visible: bool) -> str:
    first = c.first_name or t("ref.candidate")
    if contacts_visible or c.show_full_name:
        return f"{first} {c.last_name}".strip()
    return f"{first} {c.last_name[:1]}." if c.last_name else first


def contacts(c: CandidateProfile) -> dict:
    return {"full_name": f"{c.first_name} {c.last_name}".strip(), "email": c.user.email,
            "phone": c.phone, "telegram": c.telegram}
