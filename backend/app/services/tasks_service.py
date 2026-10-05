"""Regular short tasks from employers. A reviewed submission is a fresh signal: it refreshes the
candidate's profile activity (freshness component of the matching score)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.base import utcnow
from app.domain.catalog import SPEC_NAMES
from app.i18n import t
from app.models import CandidateProfile, EmployerProfile, ShortTask, TaskSubmission
from app.services import presenters, privacy


def create(db: Session, e: EmployerProfile, specialization_id: str, title: str, description: str) -> ShortTask:
    if specialization_id not in SPEC_NAMES:
        raise ValidationFailed(t("error.unknown_spec"))
    task = ShortTask(employer_id=e.id, specialization_id=specialization_id, title=title.strip(),
                  description=description.strip())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _view(db: Session, task: ShortTask, candidate: CandidateProfile | None = None) -> dict:
    n = db.scalar(select(func.count(TaskSubmission.id)).where(TaskSubmission.task_id == task.id)) or 0
    mine = None
    if candidate:
        s = db.scalar(select(TaskSubmission).where(TaskSubmission.task_id == task.id,
                                                   TaskSubmission.candidate_id == candidate.id))
        if s:
            mine = {"id": s.id, "answer": s.answer, "rating": s.rating, "reviewer_comment": s.reviewer_comment,
                    "created_at": s.created_at}
    return {"id": task.id, "title": task.title, "description": task.description, "specialization_id": task.specialization_id,
            "specialization_name": SPEC_NAMES[task.specialization_id], "is_active": task.is_active,
            "created_at": task.created_at, "company": presenters.company(task.employer), "submissions": n,
            "my_submission": mine}


def for_candidate(db: Session, c: CandidateProfile) -> list[dict]:
    spec = c.verified_specialization_id or c.specialization_id
    q = select(ShortTask).where(ShortTask.is_active.is_(True))
    if spec:
        q = q.where(ShortTask.specialization_id == spec)
    return [_view(db, task, c) for task in db.scalars(q.order_by(ShortTask.created_at.desc()))]


def for_employer(db: Session, e: EmployerProfile) -> list[dict]:
    return [_view(db, task) for task in db.scalars(select(ShortTask).where(ShortTask.employer_id == e.id)
                                             .order_by(ShortTask.created_at.desc()))]


def submit(db: Session, c: CandidateProfile, task_id: int, answer: str) -> None:
    task = db.get(ShortTask, task_id)
    if not task or not task.is_active:
        raise NotFound(t("error.task_not_found"))
    if len(answer.strip()) < 20:
        raise ValidationFailed(t("error.solution_too_short"))
    if db.scalar(select(TaskSubmission.id).where(TaskSubmission.task_id == task.id,
                                                 TaskSubmission.candidate_id == c.id)):
        raise Conflict(t("error.solution_exists"))
    db.add(TaskSubmission(task_id=task.id, candidate_id=c.id, answer=answer.strip()))
    c.last_active_at = utcnow()
    db.commit()


def submissions(db: Session, e: EmployerProfile, task_id: int) -> list[dict]:
    task = db.get(ShortTask, task_id)
    if not task or task.employer_id != e.id:
        raise NotFound(t("error.task_not_found"))
    out = []
    for s in db.scalars(select(TaskSubmission).where(TaskSubmission.task_id == task.id)
                        .order_by(TaskSubmission.created_at.desc())):
        out.append({"id": s.id, "answer": s.answer, "rating": s.rating, "reviewer_comment": s.reviewer_comment,
                    "created_at": s.created_at, "candidate_id": s.candidate_id,
                    "candidate_name": privacy.display_name(s.candidate, False)})
    return out


def review(db: Session, e: EmployerProfile, submission_id: int, rating: int, comment: str | None) -> None:
    s = db.get(TaskSubmission, submission_id)
    if not s or s.task.employer_id != e.id:
        raise NotFound(t("error.solution_not_found"))
    if not 1 <= rating <= 5:
        raise ValidationFailed(t("error.rating_range"))
    s.rating, s.reviewer_comment, s.reviewed_at = rating, comment, utcnow()
    s.candidate.last_active_at = utcnow()  # fresh, employer-validated signal
    db.commit()
