"""Testing workflow on top of the pure engine: start → answer → finish → category."""

import random
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.db.base import utcnow
from app.domain.catalog import GRADE_RANK
from app.i18n import t
from app.models import (
    AttemptStatus,
    CandidateProfile,
    Competency,
    Question,
    TestAnswer,
    TestAttempt,
    TestItem,
    TestResult,
)
from app.services import categories
from app.services.testing.generator import ItemSpec, build_blueprint, generate_form
from app.services.testing.integrity import ClientEvents, ItemTrace, assess
from app.services.testing.policy import (
    AttemptRecord,
    CandidateGradeState,
    Eligibility,
    check_eligibility,
)
from app.services.testing.scoring import (
    GradedItem,
    InvalidAnswer,
    category_label,
    grade_attempt,
    normalize_answer,
    recommendation,
    score_answer,
)

GRADES = ("junior", "middle", "senior")


def _history(db: Session, candidate_id: int) -> list[TestAttempt]:
    return list(db.scalars(
        select(TestAttempt).where(TestAttempt.candidate_id == candidate_id).order_by(TestAttempt.started_at)
    ))


def _state(p: CandidateProfile, specialization: str) -> CandidateGradeState:
    """Grade state of the category in this specialization (each category has its own lock)."""
    cat = categories.get(p, specialization)
    return CandidateGradeState(specialization if cat else None, cat.grade_id if cat else None,
                               cat.grade_locked_until if cat else None, bool(cat and cat.upgrade_eligible),
                               categories_count=len(p.categories), max_categories=get_settings().max_categories)


def expire_overdue(db: Session, candidate: CandidateProfile, now: datetime | None = None) -> None:
    """Attempts whose deadline has passed are finished automatically with the answers given."""
    now = now or utcnow()
    for att in _history(db, candidate.id):
        if att.status == AttemptStatus.IN_PROGRESS and now > att.deadline_at:
            _finish(db, candidate, att, now, expired=True)
    db.commit()


def eligibility(db: Session, candidate: CandidateProfile, specialization: str,
                now: datetime | None = None) -> list[Eligibility]:
    now = now or utcnow()
    records = [AttemptRecord(a.specialization_id, a.target_grade_id, a.finished_at,
                             a.status == AttemptStatus.IN_PROGRESS, bool(a.result and a.result.flagged))
               for a in _history(db, candidate.id)]
    days = get_settings().retake_cooldown_days
    return [check_eligibility(_state(candidate, specialization), records, specialization, g, now, days)
            for g in GRADES]


def active_attempt(db: Session, candidate: CandidateProfile) -> TestAttempt | None:
    return db.scalars(select(TestAttempt).where(TestAttempt.candidate_id == candidate.id,
                                                TestAttempt.status == AttemptStatus.IN_PROGRESS)).first()


def load_pool(db: Session, specialization: str) -> list[ItemSpec]:
    rows = db.scalars(select(Question).where(Question.specialization_id == specialization,
                                             Question.is_active.is_(True)))
    return [ItemSpec(q.id, q.code, q.specialization_id, q.competency_id, q.difficulty, q.qtype, q.text,
                     q.options, q.correct, q.family, q.irt_a, q.irt_b, q.irt_c, q.exposure_count, q.i18n or {})
            for q in rows]


def start(db: Session, candidate: CandidateProfile, specialization: str, target_grade: str,
          now: datetime | None = None, seed: int | None = None) -> TestAttempt:
    now = now or utcnow()
    if target_grade not in GRADE_RANK:
        raise ValidationFailed(t("error.unknown_grade"))
    if not candidate.specialization_id or not candidate.declared_grade_id:
        raise ValidationFailed(t("error.survey_required"),
                               code="survey_required")
    expire_overdue(db, candidate, now)
    elig = next(e for e in eligibility(db, candidate, specialization, now) if e.grade == target_grade)
    if not elig.allowed:
        raise Conflict(elig.reason or t("error.test_unavailable"), code="cooldown",
                       details={"available_at": elig.available_at.isoformat() if elig.available_at else None})

    s = get_settings()
    weights = {c.id: c.weight for c in db.scalars(select(Competency).where(
        Competency.specialization_id == specialization))}
    if not weights:
        raise NotFound(t("error.spec_not_found"))
    blueprint = build_blueprint(specialization, target_grade, weights, s.test_length)
    seen = {it.question_id for att in _history(db, candidate.id) for it in att.items}
    seed = seed if seed is not None else random.SystemRandom().randrange(2**31)
    form = generate_form(blueprint, load_pool(db, specialization), random.Random(seed), seen)

    attempt = TestAttempt(
        candidate_id=candidate.id, specialization_id=specialization, target_grade_id=target_grade,
        status=AttemptStatus.IN_PROGRESS, seed=seed, blueprint=blueprint.to_dict(),
        form_mean_b=round(sum(f.b for f in form) / len(form), 3), started_at=now,
        deadline_at=now + timedelta(minutes=s.test_time_limit_minutes),
    )
    for f in form:
        attempt.items.append(TestItem(
            question_id=f.question_id, position=f.position, competency_id=f.competency,
            difficulty=f.difficulty, qtype=f.qtype, text=f.text, options=f.options, correct=f.correct,
            irt_a=f.a, irt_b=f.b, irt_c=f.c, params=f.params, family=f.family, i18n=f.i18n or None,
        ))
    db.add(attempt)
    for q in db.scalars(select(Question).where(Question.id.in_([f.question_id for f in form]))):
        q.exposure_count += 1
    candidate.last_active_at = now
    db.commit()
    db.refresh(attempt)
    return attempt


def get_attempt(db: Session, candidate: CandidateProfile, attempt_id: int) -> TestAttempt:
    att = db.get(TestAttempt, attempt_id)
    if not att or att.candidate_id != candidate.id:
        raise NotFound(t("error.attempt_not_found"))
    return att


def _merge_client(att: TestAttempt, client: dict | None) -> None:
    """Client counters are cumulative: keep the maximum ever reported (a reload cannot reset them)."""
    if not client:
        return
    cur = dict(att.client_events or {})
    for k in ("focus_lost", "away_ms", "copies"):
        cur[k] = max(int(cur.get(k, 0)), int(client.get(k) or 0))
    att.client_events = cur


def answer(db: Session, candidate: CandidateProfile, attempt_id: int, item_id: int, raw: list,
           now: datetime | None = None, time_ms: int | None = None, pasted: bool = False,
           client: dict | None = None) -> TestAttempt:
    now = now or utcnow()
    att = get_attempt(db, candidate, attempt_id)
    if att.status != AttemptStatus.IN_PROGRESS:
        raise Conflict(t("error.attempt_closed"), code="attempt_closed")
    if now > att.deadline_at:
        _finish(db, candidate, att, now, expired=True)
        db.commit()
        raise Conflict(t("error.attempt_expired"), code="attempt_expired")
    item = next((i for i in att.items if i.id == item_id), None)
    if not item:
        raise NotFound(t("error.item_not_in_attempt"))
    try:
        value = normalize_answer(item.qtype, len(item.options), raw)
    except InvalidAnswer as e:
        raise ValidationFailed(str(e), code="invalid_answer") from e
    ok, credit = score_answer(item.qtype, item.correct, value)
    if item.answer:
        item.answer.answer, item.answer.is_correct, item.answer.credit = value, ok, credit
        item.answer.answered_at = now
        # a changed answer: time adds up, a paste is remembered
        if time_ms is not None:
            item.answer.time_ms = (item.answer.time_ms or 0) + time_ms
        item.answer.pasted = item.answer.pasted or pasted
    else:
        item.answer = TestAnswer(answer=value, is_correct=ok, credit=credit, answered_at=now, time_ms=time_ms,
                                 pasted=pasted)
    _merge_client(att, client)
    db.commit()
    return att


def finish(db: Session, candidate: CandidateProfile, attempt_id: int, now: datetime | None = None,
           client: dict | None = None) -> TestResult:
    now = now or utcnow()
    att = get_attempt(db, candidate, attempt_id)
    if att.status == AttemptStatus.IN_PROGRESS:
        _merge_client(att, client)
    if att.status != AttemptStatus.IN_PROGRESS:
        if att.result:
            return att.result
        raise Conflict(t("error.attempt_closed"), code="attempt_closed")
    result = _finish(db, candidate, att, now, expired=now > att.deadline_at)
    db.commit()
    return result


def _finish(db: Session, candidate: CandidateProfile, att: TestAttempt, now: datetime,
            expired: bool = False) -> TestResult:
    graded = []
    for it in att.items:
        a = it.answer
        graded.append(GradedItem(it.competency_id, it.irt_a, it.irt_b, it.irt_c,
                                 bool(a and a.is_correct), a.credit if a else 0.0, it.family is not None))
    out = grade_attempt(graded, att.target_grade_id)
    att.status = AttemptStatus.EXPIRED if expired else AttemptStatus.FINISHED
    att.finished_at = now

    # behavioural integrity: a «risk» result is confirmed by one fresh form, like a leak flag
    ev = att.client_events or {}
    integrity = assess(
        [ItemTrace(it.qtype, it.difficulty, it.irt_a, it.irt_b, it.irt_c, bool(it.answer and it.answer.is_correct),
                   it.answer.time_ms if it.answer else None, bool(it.answer and it.answer.pasted),
                   it.family is not None) for it in att.items],
        out.theta, ClientEvents(int(ev.get("focus_lost", 0)), int(ev.get("away_ms", 0)), int(ev.get("copies", 0))),
        int((now - att.started_at).total_seconds() * 1000),
    )
    att.integrity = integrity.to_dict()
    if integrity.level == "risk" and out.passed:
        out.flagged, out.passed, out.upgrade_eligible = True, False, False
        out.outcome, out.verified_grade = "needs_confirmation", None

    grade_changed = False
    blocked = False
    spec = att.specialization_id
    cat = categories.get(candidate, spec)  # categories are independent per specialization
    current = cat.grade_id if cat else None

    if out.passed:
        target = att.target_grade_id
        if cat is not None and current == target:
            # re-confirmation refreshes the verified data, no grade change
            cat.verified_at = now
        else:
            locked = cat is not None and cat.grade_locked_until is not None and now < cat.grade_locked_until
            fast_track = (cat is not None and GRADE_RANK[target] - GRADE_RANK[current] == 1
                          and cat.upgrade_eligible)
            if locked and not fast_track:
                blocked = True  # guarded at start(), kept as a safety net
            else:
                grade_changed = True
                cat = categories.ensure(candidate, spec, now)
                cat.grade_id = target
                cat.verified_at = now
                cat.grade_locked_until = now + timedelta(days=get_settings().grade_change_cooldown_days)
        if not blocked:
            cat.upgrade_eligible = out.upgrade_eligible
            cat.theta = out.theta
            cat.scaled_score = out.scaled_score
            cat.confidence = out.confidence
            cat.competency_scores = out.competency_scores
    elif cat is not None and GRADE_RANK[att.target_grade_id] > GRADE_RANK[current]:
        # failed upgrade attempt: the verified grade is kept, the fast track is used up
        cat.upgrade_eligible = False
    categories.sync_primary(candidate)

    verified_for_result = att.target_grade_id if out.passed and not blocked else None
    result = TestResult(
        attempt_id=att.id, candidate_id=candidate.id, theta=out.theta, theta_se=out.theta_se,
        scaled_score=out.scaled_score, raw_percent=out.raw_percent, outcome=out.outcome,
        passed=out.passed, confidence=out.confidence, verified_grade_id=verified_for_result,
        grade_changed=grade_changed, grade_change_blocked=blocked,
        flagged=out.flagged, person_fit=out.person_fit, leak_z=out.leak_z,
        category_label=category_label(spec, verified_for_result),
        competency_scores=out.competency_scores,
        recommendation=recommendation(out.outcome, att.target_grade_id, expired),
        created_at=now,
    )
    att.result = result
    candidate.last_active_at = now
    candidate.profile_updated_at = now
    db.flush()
    return result


def results(db: Session, candidate: CandidateProfile) -> list[TestResult]:
    return list(db.scalars(select(TestResult).where(TestResult.candidate_id == candidate.id)
                           .order_by(TestResult.created_at.desc())))


def ensure_owner(att: TestAttempt, candidate: CandidateProfile) -> None:
    if att.candidate_id != candidate.id:
        raise Forbidden(t("error.attempt_forbidden"))
