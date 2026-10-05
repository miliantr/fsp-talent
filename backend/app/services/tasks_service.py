"""Regular short tasks from employers. A reviewed submission is a fresh signal: it refreshes the
candidate's profile activity (freshness component of the matching score)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.base import utcnow
from app.domain.catalog import SPEC_NAMES
from app.models import CandidateProfile, EmployerProfile, ShortTask, TaskSubmission
from app.services import presenters, privacy


def create(db: Session, e: EmployerProfile, specialization_id: str, title: str, description: str) -> ShortTask:
    if specialization_id not in SPEC_NAMES:
        raise ValidationFailed("Неизвестная специализация")
    t = ShortTask(employer_id=e.id, specialization_id=specialization_id, title=title.strip(),
                  description=description.strip())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _view(db: Session, t: ShortTask, candidate: CandidateProfile | None = None) -> dict:
    n = db.scalar(select(func.count(TaskSubmission.id)).where(TaskSubmission.task_id == t.id)) or 0
    mine = None
    if candidate:
        s = db.scalar(select(TaskSubmission).where(TaskSubmission.task_id == t.id,
                                                   TaskSubmission.candidate_id == candidate.id))
        if s:
            mine = {"id": s.id, "answer": s.answer, "rating": s.rating, "reviewer_comment": s.reviewer_comment,
                    "created_at": s.created_at}
    return {"id": t.id, "title": t.title, "description": t.description, "specialization_id": t.specialization_id,
            "specialization_name": SPEC_NAMES[t.specialization_id], "is_active": t.is_active,
            "created_at": t.created_at, "company": presenters.company(t.employer), "submissions": n,
            "my_submission": mine}


def for_candidate(db: Session, c: CandidateProfile) -> list[dict]:
    spec = c.verified_specialization_id or c.specialization_id
    q = select(ShortTask).where(ShortTask.is_active.is_(True))
    if spec:
        q = q.where(ShortTask.specialization_id == spec)
    return [_view(db, t, c) for t in db.scalars(q.order_by(ShortTask.created_at.desc()))]


def for_employer(db: Session, e: EmployerProfile) -> list[dict]:
    return [_view(db, t) for t in db.scalars(select(ShortTask).where(ShortTask.employer_id == e.id)
                                             .order_by(ShortTask.created_at.desc()))]


def submit(db: Session, c: CandidateProfile, task_id: int, answer: str) -> None:
    t = db.get(ShortTask, task_id)
    if not t or not t.is_active:
        raise NotFound("Задание не найдено")
    if len(answer.strip()) < 20:
        raise ValidationFailed("Опишите решение или подход подробнее (от 20 символов)")
    if db.scalar(select(TaskSubmission.id).where(TaskSubmission.task_id == t.id,
                                                 TaskSubmission.candidate_id == c.id)):
        raise Conflict("Решение уже отправлено")
    db.add(TaskSubmission(task_id=t.id, candidate_id=c.id, answer=answer.strip()))
    c.last_active_at = utcnow()
    db.commit()


def submissions(db: Session, e: EmployerProfile, task_id: int) -> list[dict]:
    t = db.get(ShortTask, task_id)
    if not t or t.employer_id != e.id:
        raise NotFound("Задание не найдено")
    out = []
    for s in db.scalars(select(TaskSubmission).where(TaskSubmission.task_id == t.id)
                        .order_by(TaskSubmission.created_at.desc())):
        out.append({"id": s.id, "answer": s.answer, "rating": s.rating, "reviewer_comment": s.reviewer_comment,
                    "created_at": s.created_at, "candidate_id": s.candidate_id,
                    "candidate_name": privacy.display_name(s.candidate, False)})
    return out


def review(db: Session, e: EmployerProfile, submission_id: int, rating: int, comment: str | None) -> None:
    s = db.get(TaskSubmission, submission_id)
    if not s or s.task.employer_id != e.id:
        raise NotFound("Решение не найдено")
    if not 1 <= rating <= 5:
        raise ValidationFailed("Оценка от 1 до 5")
    s.rating, s.reviewer_comment, s.reviewed_at = rating, comment, utcnow()
    s.candidate.last_active_at = utcnow()  # fresh, employer-validated signal
    db.commit()
