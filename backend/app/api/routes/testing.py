from fastapi import APIRouter, status

from app.api.deps import DB, Candidate
from app.api.responses import errors
from app.core.config import get_settings
from app.core.errors import NotFound
from app.db.base import utcnow
from app.domain.catalog import GRADE_NAMES
from app.i18n import t
from app.models import TestAttempt, TestResult
from app.schemas.testing import (
    AnswerIn,
    AnswerOut,
    AttemptOut,
    FinishIn,
    ResultOut,
    StartIn,
    TestingStatusOut,
)
from app.services import categories
from app.services.presenters import attempt_view, result_view
from app.services.presenters import categories as category_list
from app.services.testing import service

router = APIRouter(prefix="/candidate/testing", tags=["Тестирование"], responses=errors(401, 403))


def _brief(r: TestResult) -> dict:
    return {"attempt_id": r.attempt_id, "specialization_id": r.attempt.specialization_id,
            "target_grade": r.attempt.target_grade_id, "outcome": r.outcome, "passed": r.passed,
            "scaled_score": r.scaled_score, "verified_grade": r.verified_grade_id,
            "category_label": r.category_label, "created_at": r.created_at}


@router.get("", response_model=TestingStatusOut,
            summary="Статус: доступные тесты по грейдам, кулдауны, активная попытка, история")
def status_(c: Candidate, db: DB, specialization_id: str | None = None):
    service.expire_overdue(db, c)
    spec = specialization_id or c.specialization_id or c.verified_specialization_id or "backend"
    act: TestAttempt | None = service.active_attempt(db, c)
    s = get_settings()
    cat = categories.get(c, spec)
    return {
        "specialization_id": c.specialization_id, "declared_grade_id": c.declared_grade_id,
        "verified_specialization_id": c.verified_specialization_id, "verified_grade_id": c.verified_grade_id,
        "viewed_specialization_id": spec, "viewed_grade_id": cat.grade_id if cat else None,
        "grade_locked_until": cat.grade_locked_until if cat else None,
        "upgrade_eligible": bool(cat and cat.upgrade_eligible),
        "categories": category_list(c), "max_categories": s.max_categories,
        "active_attempt": {"id": act.id, "specialization_id": act.specialization_id,
                           "target_grade": act.target_grade_id, "started_at": act.started_at,
                           "deadline_at": act.deadline_at, "answered": sum(1 for i in act.items if i.answer),
                           "total": len(act.items)} if act else None,
        "eligibility": [{**e.__dict__, "grade_name": GRADE_NAMES[e.grade]}
                        for e in service.eligibility(db, c, spec)],
        "history": [_brief(r) for r in service.results(db, c)],
        "rules": {"test_length": s.test_length, "time_limit_minutes": s.test_time_limit_minutes,
                  "retake_cooldown_days": s.retake_cooldown_days,
                  "grade_change_cooldown_days": s.grade_change_cooldown_days},
    }


@router.post("/start", response_model=AttemptOut, status_code=status.HTTP_201_CREATED,
             responses=errors(404, 409, 422), summary="Сгенерировать индивидуальный вариант теста")
def start(body: StartIn, c: Candidate, db: DB):
    att = service.start(db, c, body.specialization_id, body.target_grade)
    return attempt_view(att, utcnow())


@router.get("/attempts/{attempt_id}", response_model=AttemptOut, responses=errors(404),
            summary="Вопросы попытки (без правильных ответов)")
def get_attempt(attempt_id: int, c: Candidate, db: DB):
    return attempt_view(service.get_attempt(db, c, attempt_id), utcnow())


@router.post("/answer", response_model=AnswerOut, responses=errors(404, 409, 422), summary="Сохранить ответ")
def answer(body: AnswerIn, c: Candidate, db: DB):
    att = service.answer(db, c, body.attempt_id, body.item_id, body.answer)
    return AnswerOut(item_id=body.item_id, saved=True, answered=sum(1 for i in att.items if i.answer),
                     total=len(att.items))


@router.post("/finish", response_model=ResultOut, responses=errors(404, 409),
             summary="Завершить тест: грейд, категория, компетенции, уверенность")
def finish(body: FinishIn, c: Candidate, db: DB):
    return result_view(service.finish(db, c, body.attempt_id))


@router.get("/results/{attempt_id}", response_model=ResultOut, responses=errors(404), summary="Результат попытки")
def result(attempt_id: int, c: Candidate, db: DB):
    att = service.get_attempt(db, c, attempt_id)
    if not att.result:
        raise NotFound(t("error.attempt_not_finished"))
    return result_view(att.result)
