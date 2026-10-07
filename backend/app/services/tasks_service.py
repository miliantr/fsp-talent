"""Regular short tasks (TЗ: «the system periodically offers the candidate a short task from an
employer — to solve it or to propose an approach»).

  * Format. «solve» — a concrete answer (a number or a short text) checked automatically against the
    employer's key; «approach» — a free-text approach the employer scores with a 3-criterion rubric
    (correctness, completeness, reasoning: 0–2 each). For triage an approach also gets an automatic
    pre-score — the share of the employer's key points the answer covers; the final score is the
    employer's.
  * Audience. «targeted» — the system offers the task to suitable candidates one at a time;
    «category» — an open challenge for the whole category (specialization, optionally a grade).
  * Offer rule. A verified candidate holds at most one open offer and gets a new one at most every
    TASK_OFFER_INTERVAL_DAYS. The task is picked by: grade fit; the employer is considering the
    candidate for the requirement the task is linked to; the task checks a competency the test
    confirmed weakly; novelty; spreading the employer's review load (max_offers). An offer expires
    after the task's time limit; a declined one is not offered again.
  * Effect. A submission refreshes the profile (freshness component of matching) and is a fresh
    signal on the candidate card. It never changes the grade — only the test does.
"""

import math
import re
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.base import utcnow
from app.domain.catalog import COMPETENCIES, GRADE_NAMES, GRADE_RANK, SPEC_NAMES
from app.i18n import competency_name, msg, render, t
from app.models import (
    AssignmentStatus,
    CandidateProfile,
    EmployerProfile,
    Job,
    MatchResult,
    ShortTask,
    SubmissionStatus,
    TaskAssignment,
    TaskAudience,
    TaskMode,
    TaskSubmission,
)
from app.services import categories, presenters, privacy
from app.services.testing.scoring import category_label

COMPETENCY_SPEC = {cid: spec for cid, spec, _, _ in COMPETENCIES}
RUBRIC = ("correctness", "completeness", "reasoning")  # 0..2 each
SIGNAL_WINDOW_DAYS = 90


# ------------------------------------------------------------------ automatic checks

def check_solution(spec: dict, answer: str) -> bool:
    """Auto-check of a «solve» task: a number within the tolerance or one of the accepted texts."""
    if spec.get("kind") == "number":
        try:
            value = float(answer.strip().replace(",", ".").replace(" ", ""))
        except ValueError as e:
            raise ValidationFailed(t("error.task_answer_number")) from e
        return abs(value - float(spec["value"])) <= float(spec.get("tolerance") or 0) + 1e-9
    norm = _normalize(answer)
    return any(norm == _normalize(a) for a in spec.get("accepted", []))


_WORD = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)
_STOP = {"и", "в", "на", "с", "по", "для", "не", "что", "как", "или", "это", "при", "из", "от", "до", "а", "но",
         "the", "and", "for", "with", "to", "of", "in", "on", "a", "an", "or", "is", "be", "by", "it", "at"}


def _normalize(text: str) -> str:
    return " ".join(_WORD.findall(text.lower().replace("ё", "е")))


def _stems(text: str) -> set[str]:
    """Crude language-agnostic stemming: words cut to 5 characters (enough to match word forms of
    «идемпотентность / идемпотентный», «retry / retries» without a morphology library)."""
    return {w[:5] for w in _normalize(text).split() if w not in _STOP and len(w) > 1}


def key_point_coverage(answer: str, points: list[str]) -> tuple[float | None, list[str], list[str]]:
    """Share of the reference ideas the answer covers: a point counts when ≥ 60% of its content words
    occur in the answer. A pre-score for triage only — the employer's rubric is the final score."""
    if not points:
        return None, [], []
    have = _stems(answer)
    matched, missed = [], []
    for p in points:
        words = _stems(p)
        hit = len(words & have) / len(words) if words else 0
        (matched if hit >= 0.6 else missed).append(p)
    return round(len(matched) / len(points), 3), matched, missed


# ------------------------------------------------------------------ employer: publish

def _validate(db: Session, e: EmployerProfile, data: dict) -> None:
    spec = data["specialization_id"]
    if spec not in SPEC_NAMES:
        raise ValidationFailed(t("error.unknown_spec"))
    if data.get("grade_id") and data["grade_id"] not in GRADE_RANK:
        raise ValidationFailed(t("error.unknown_grade"))
    if data.get("competency_id") and COMPETENCY_SPEC.get(data["competency_id"]) != spec:
        raise ValidationFailed(t("error.task_competency"))
    if data.get("job_id"):
        job = db.get(Job, data["job_id"])
        if not job or job.employer_id != e.id:
            raise NotFound(t("error.requirement_not_found"))
    if data.get("mode", TaskMode.APPROACH) == TaskMode.SOLVE:
        a = data.get("answer_spec") or {}
        ok = (a.get("kind") == "number" and isinstance(a.get("value"), (int, float))) or \
             (a.get("kind") == "text" and any(str(x).strip() for x in a.get("accepted") or []))
        if not ok:
            raise ValidationFailed(t("error.task_answer_spec"))


def create(db: Session, e: EmployerProfile, data: dict) -> ShortTask:
    _validate(db, e, data)
    mode = data.get("mode") or TaskMode.APPROACH
    task = ShortTask(
        employer_id=e.id, specialization_id=data["specialization_id"], title=data["title"].strip(),
        description=data["description"].strip(), mode=mode,
        audience=data.get("audience") or TaskAudience.TARGETED, grade_id=data.get("grade_id"),
        job_id=data.get("job_id"), competency_id=data.get("competency_id"),
        answer_spec=data.get("answer_spec") if mode == TaskMode.SOLVE else None,
        key_points=[p.strip() for p in data.get("key_points") or [] if p.strip()],
        time_limit_days=data.get("time_limit_days") or 7, max_offers=data.get("max_offers") or 20,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def set_active(db: Session, e: EmployerProfile, task_id: int, active: bool) -> ShortTask:
    task = db.get(ShortTask, task_id)
    if not task or task.employer_id != e.id:
        raise NotFound(t("error.task_not_found"))
    task.is_active = active
    db.commit()
    return task


# ------------------------------------------------------------------ offers

def _grade_fit(task: ShortTask, grade: str) -> float | None:
    if not task.grade_id:
        return 1.0
    d = abs(GRADE_RANK[task.grade_id] - GRADE_RANK[grade])
    return 2.0 if d == 0 else 0.5 if d == 1 else None


def _candidate_score(db: Session, c: CandidateProfile, task: ShortTask, now: datetime,
                     offers: int) -> tuple[float, list[dict]] | None:
    """Usefulness of offering `task` to `c` (None — not suitable) and the reasons, as message objects."""
    cat = categories.get(c, task.specialization_id)
    if cat is None:
        return None
    fit = _grade_fit(task, cat.grade_id)
    if fit is None:
        return None
    score = fit + (0.3 if cat.is_primary else 0.0)
    reasons = [msg("task.reason.category", label=category_label(cat.specialization_id, cat.grade_id))]
    if task.job_id:
        m = db.scalar(select(MatchResult).where(MatchResult.job_id == task.job_id, MatchResult.candidate_id == c.id))
        if m is not None:
            # the employer is considering this candidate for the linked requirement: the most useful signal
            score += 2.0 + m.score
            reasons.append(msg("task.reason.requirement", title=task.job.title if task.job else ""))
    if task.competency_id:
        tested = (cat.competency_scores or {}).get(task.competency_id)
        score += 0.8 if tested is None else 1.0 - tested / 100
        reasons.append(msg("task.reason.competency_weak" if tested is not None and tested < 60
                           else "task.reason.competency", name={"competency": task.competency_id},
                           score=tested if tested is not None else 0))
    age = max(0.0, (now - task.created_at).days)
    score += 0.2 * math.exp(-age / 14) - 0.05 * offers
    return score, reasons


def _offers_count(db: Session, task_id: int) -> int:
    return db.scalar(select(func.count(TaskAssignment.id)).where(TaskAssignment.task_id == task_id)) or 0


def expire_overdue(db: Session, c: CandidateProfile, now: datetime) -> None:
    for a in db.scalars(select(TaskAssignment).where(TaskAssignment.candidate_id == c.id,
                                                     TaskAssignment.status == AssignmentStatus.OFFERED,
                                                     TaskAssignment.due_at < now)):
        a.status = AssignmentStatus.EXPIRED


def next_offer_at(db: Session, c: CandidateProfile) -> datetime | None:
    last = db.scalar(select(func.max(TaskAssignment.offered_at)).where(TaskAssignment.candidate_id == c.id,
                                                                       TaskAssignment.source == "system"))
    return last + timedelta(days=get_settings().task_offer_interval_days) if last else None


def offer_due(db: Session, c: CandidateProfile, now: datetime | None = None) -> TaskAssignment | None:
    """Offers the next task to the candidate if one is due (lazily on reading the tasks and by the
    periodic job). Returns the new assignment or None."""
    now = now or utcnow()
    expire_overdue(db, c, now)
    if not c.categories or not c.user.is_active:
        db.commit()
        return None
    open_offer = db.scalar(select(TaskAssignment.id).where(TaskAssignment.candidate_id == c.id,
                                                           TaskAssignment.status == AssignmentStatus.OFFERED))
    due = next_offer_at(db, c)
    if open_offer or (due and now < due):
        db.commit()
        return None
    seen = set(db.scalars(select(TaskAssignment.task_id).where(TaskAssignment.candidate_id == c.id)))
    seen |= set(db.scalars(select(TaskSubmission.task_id).where(TaskSubmission.candidate_id == c.id)))
    specs = [k.specialization_id for k in c.categories]
    best: tuple[float, ShortTask, list[dict]] | None = None
    for task in db.scalars(select(ShortTask).where(ShortTask.is_active.is_(True),
                                                   ShortTask.audience == TaskAudience.TARGETED,
                                                   ShortTask.specialization_id.in_(specs))):
        if task.id in seen:
            continue
        offers = _offers_count(db, task.id)
        if offers >= task.max_offers:
            continue
        scored = _candidate_score(db, c, task, now, offers)
        if scored and (best is None or scored[0] > best[0]):
            best = (scored[0], task, scored[1])
    if best is None:
        db.commit()
        return None
    _, task, reasons = best
    a = TaskAssignment(task_id=task.id, candidate_id=c.id, source="system", reason=reasons,
                       status=AssignmentStatus.OFFERED, offered_at=now,
                       due_at=now + timedelta(days=task.time_limit_days))
    db.add(a)
    db.commit()
    return a


def offer_all_due(db: Session, now: datetime | None = None) -> int:
    """Periodic job: one pass over verified candidates who are open to offers."""
    now = now or utcnow()
    count = 0
    for c in db.scalars(select(CandidateProfile).where(CandidateProfile.verified_grade_id.is_not(None),
                                                       CandidateProfile.open_to_offers.is_(True))):
        count += offer_due(db, c, now) is not None
    return count


def offer_to(db: Session, e: EmployerProfile, task_id: int, candidate_id: int, now: datetime | None = None) -> None:
    """An employer offers its task to a particular candidate (e.g. from a shortlist)."""
    now = now or utcnow()
    task = db.get(ShortTask, task_id)
    if not task or task.employer_id != e.id or not task.is_active:
        raise NotFound(t("error.task_not_found"))
    c = db.get(CandidateProfile, candidate_id)
    if not c or not (c.is_searchable or privacy.has_relationship(db, e, c)):
        raise NotFound(t("error.candidate_unavailable"))
    if db.scalar(select(TaskAssignment.id).where(TaskAssignment.task_id == task.id,
                                                 TaskAssignment.candidate_id == c.id)) or \
            db.scalar(select(TaskSubmission.id).where(TaskSubmission.task_id == task.id,
                                                      TaskSubmission.candidate_id == c.id)):
        raise Conflict(t("error.task_already_offered"), code="task_already_offered")
    db.add(TaskAssignment(task_id=task.id, candidate_id=c.id, source="employer",
                          reason=[msg("task.reason.employer", company=e.company_name or t("ref.company"))],
                          status=AssignmentStatus.OFFERED, offered_at=now,
                          due_at=now + timedelta(days=task.time_limit_days)))
    db.commit()


def decline(db: Session, c: CandidateProfile, assignment_id: int, now: datetime | None = None) -> None:
    a = db.get(TaskAssignment, assignment_id)
    if not a or a.candidate_id != c.id:
        raise NotFound(t("error.assignment_not_found"))
    if a.status != AssignmentStatus.OFFERED:
        raise Conflict(t("error.assignment_closed"), code="assignment_closed")
    a.status, a.responded_at = AssignmentStatus.DECLINED, now or utcnow()
    db.commit()


# ------------------------------------------------------------------ candidate

def _task_view(task: ShortTask) -> dict:
    return {"id": task.id, "title": task.title, "description": task.description, "mode": task.mode,
            "audience": task.audience, "answer_kind": (task.answer_spec or {}).get("kind"),
            "specialization_id": task.specialization_id, "specialization_name": SPEC_NAMES[task.specialization_id],
            "grade_id": task.grade_id, "grade_name": GRADE_NAMES.get(task.grade_id) if task.grade_id else None,
            "competency_id": task.competency_id,
            "competency_name": competency_name(task.competency_id) if task.competency_id else None,
            "requirement_title": task.job.title if task.job else None, "time_limit_days": task.time_limit_days,
            "is_active": task.is_active, "created_at": task.created_at, "company": presenters.company(task.employer)}


def _my_result(s: TaskSubmission) -> dict:
    """What the candidate sees: the auto-check verdict or the employer's rubric (never the key)."""
    return {"id": s.id, "task_id": s.task_id, "task_title": s.task.title, "mode": s.task.mode,
            "company": presenters.company(s.task.employer), "answer": s.answer, "status": s.status,
            "correct": (s.auto_score or 0) >= 1 if s.task.mode == TaskMode.SOLVE else None,
            "rubric": s.rubric, "score": round(s.score * 100) if s.score is not None else None,
            "reviewer_comment": s.reviewer_comment, "created_at": s.created_at, "reviewed_at": s.reviewed_at}


def for_candidate(db: Session, c: CandidateProfile, now: datetime | None = None) -> dict:
    now = now or utcnow()
    offer_due(db, c, now)
    offers = db.scalars(select(TaskAssignment).where(TaskAssignment.candidate_id == c.id,
                                                     TaskAssignment.status == AssignmentStatus.OFFERED)
                        .order_by(TaskAssignment.offered_at.desc()))
    done = {s.task_id for s in c.task_submissions}
    specs = {k.specialization_id: k.grade_id for k in c.categories}
    challenges = []
    for task in db.scalars(select(ShortTask).where(ShortTask.is_active.is_(True),
                                                   ShortTask.audience == TaskAudience.CATEGORY)
                           .order_by(ShortTask.created_at.desc())):
        grade = specs.get(task.specialization_id)
        if grade is None or task.id in done or _grade_fit(task, grade) is None:
            continue
        challenges.append(_task_view(task))
    history = sorted(c.task_submissions, key=lambda s: s.created_at, reverse=True)
    due = next_offer_at(db, c)
    return {
        "offered": [{"assignment_id": a.id, "source": a.source, "reasons": [render(r) for r in a.reason or []],
                     "offered_at": a.offered_at, "due_at": a.due_at, "task": _task_view(a.task)} for a in offers],
        "challenges": challenges,
        "history": [_my_result(s) for s in history],
        "next_offer_at": due if due and due > now else None,
        "interval_days": get_settings().task_offer_interval_days,
        "verified": bool(c.categories),
    }


def submit(db: Session, c: CandidateProfile, task_id: int, answer: str, now: datetime | None = None) -> dict:
    now = now or utcnow()
    task = db.get(ShortTask, task_id)
    if not task or not task.is_active:
        raise NotFound(t("error.task_not_found"))
    if db.scalar(select(TaskSubmission.id).where(TaskSubmission.task_id == task.id,
                                                 TaskSubmission.candidate_id == c.id)):
        raise Conflict(t("error.solution_exists"))
    assignment = db.scalar(select(TaskAssignment).where(TaskAssignment.task_id == task.id,
                                                        TaskAssignment.candidate_id == c.id))
    if task.audience == TaskAudience.TARGETED:
        # an addressed task: only the candidate it was offered to, before the deadline
        if assignment is None or assignment.status in (AssignmentStatus.DECLINED,):
            raise Conflict(t("error.task_not_offered"), code="task_not_offered")
        if assignment.status == AssignmentStatus.EXPIRED or now > assignment.due_at:
            assignment.status = AssignmentStatus.EXPIRED
            db.commit()
            raise Conflict(t("error.task_expired"), code="task_expired")
    elif categories.get(c, task.specialization_id) is None:
        raise Conflict(t("error.task_other_category"), code="task_not_offered")

    answer = answer.strip()
    sub = TaskSubmission(task_id=task.id, candidate_id=c.id, assignment_id=assignment.id if assignment else None,
                         answer=answer, created_at=now)
    if task.mode == TaskMode.SOLVE:
        ok = check_solution(task.answer_spec or {}, answer)
        sub.auto_score = sub.score = 1.0 if ok else 0.0
        sub.status, sub.reviewed_at = SubmissionStatus.CHECKED, now
        sub.auto_detail = {"correct": ok}
    else:
        if len(answer) < 20:
            raise ValidationFailed(t("error.solution_too_short"))
        cov, matched, missed = key_point_coverage(answer, task.key_points or [])
        sub.auto_score, sub.status = cov, SubmissionStatus.PENDING_REVIEW
        sub.auto_detail = {"matched": matched, "missed": missed}
    if assignment is not None:
        assignment.status, assignment.responded_at = AssignmentStatus.SUBMITTED, now
    db.add(sub)
    c.last_active_at = now  # a fresh signal: the profile is up to date
    db.commit()
    db.refresh(sub)
    return _my_result(sub)


# ------------------------------------------------------------------ employer

def for_employer(db: Session, e: EmployerProfile) -> list[dict]:
    out = []
    for task in db.scalars(select(ShortTask).where(ShortTask.employer_id == e.id).order_by(ShortTask.created_at.desc())):
        subs = list(db.scalars(select(TaskSubmission).where(TaskSubmission.task_id == task.id)))
        scored = [s.score for s in subs if s.score is not None]
        out.append({**_task_view(task), "job_id": task.job_id, "answer_spec": task.answer_spec,
                    "key_points": task.key_points or [], "max_offers": task.max_offers,
                    "stats": {"offered": _offers_count(db, task.id), "submitted": len(subs),
                              "pending_review": sum(1 for s in subs if s.status == SubmissionStatus.PENDING_REVIEW),
                              "avg_score": round(100 * sum(scored) / len(scored)) if scored else None}})
    return out


def submissions(db: Session, e: EmployerProfile, task_id: int) -> list[dict]:
    task = db.get(ShortTask, task_id)
    if not task or task.employer_id != e.id:
        raise NotFound(t("error.task_not_found"))
    rows = list(db.scalars(select(TaskSubmission).where(TaskSubmission.task_id == task.id)))
    # unreviewed answers first, the best pre-scores on top: the reviewer starts with the strongest
    rows.sort(key=lambda s: (s.status != SubmissionStatus.PENDING_REVIEW, -(s.auto_score or 0), s.created_at))
    out = []
    for s in rows:
        c = s.candidate
        out.append({"id": s.id, "answer": s.answer, "status": s.status, "auto_score": s.auto_score,
                    "auto_detail": s.auto_detail, "rubric": s.rubric,
                    "score": round(s.score * 100) if s.score is not None else None, "rating": s.rating,
                    "reviewer_comment": s.reviewer_comment, "created_at": s.created_at, "candidate_id": c.id,
                    "candidate_name": privacy.display_name(c, False),
                    "category_label": category_label(c.verified_specialization_id, c.verified_grade_id)})
    return out


def review(db: Session, e: EmployerProfile, submission_id: int, rubric: dict, comment: str | None,
           now: datetime | None = None) -> None:
    now = now or utcnow()
    s = db.get(TaskSubmission, submission_id)
    if not s or s.task.employer_id != e.id:
        raise NotFound(t("error.solution_not_found"))
    if set(rubric) != set(RUBRIC) or any(not isinstance(v, int) or not 0 <= v <= 2 for v in rubric.values()):
        raise ValidationFailed(t("error.rubric_range"))
    s.rubric = {k: rubric[k] for k in RUBRIC}
    s.score = round(sum(s.rubric.values()) / (2 * len(RUBRIC)), 3)
    s.rating = 1 + round(4 * s.score)
    s.status, s.reviewer_comment, s.reviewed_at = SubmissionStatus.REVIEWED, comment, now
    s.candidate.last_active_at = now  # fresh, employer-validated signal
    db.commit()


# ------------------------------------------------------------------ signal for employers

def signal(c: CandidateProfile, now: datetime | None = None) -> dict | None:
    """Recent task results of the candidate — a fresh signal on the card (last 90 days)."""
    now = now or utcnow()
    recent = [s for s in c.task_submissions if (now - s.created_at).days <= SIGNAL_WINDOW_DAYS]
    if not recent:
        return None
    scored = [s for s in recent if s.score is not None]
    last = max(recent, key=lambda s: s.reviewed_at or s.created_at)
    return {"done": len(scored), "pending": sum(1 for s in recent if s.status == SubmissionStatus.PENDING_REVIEW),
            "avg_score": round(100 * sum(s.score for s in scored) / len(scored)) if scored else None,
            "last_title": last.task.title, "last_score": round(last.score * 100) if last.score is not None else None,
            "last_at": last.reviewed_at or last.created_at}
