from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import Category, CompetencyScore, GradeId, SpecId


class EligibilityOut(BaseModel):
    grade: str
    grade_name: str
    allowed: bool
    kind: str
    reason: str | None = None
    available_at: datetime | None = None


class ResultBrief(BaseModel):
    attempt_id: int
    specialization_id: str
    target_grade: str
    outcome: str
    passed: bool
    scaled_score: int
    verified_grade: str | None
    category_label: str | None
    created_at: datetime


class AttemptBrief(BaseModel):
    id: int
    specialization_id: str
    target_grade: str
    started_at: datetime
    deadline_at: datetime
    answered: int
    total: int


class TestingRules(BaseModel):
    test_length: int
    time_limit_minutes: int
    retake_cooldown_days: int
    grade_change_cooldown_days: int


class TestingStatusOut(BaseModel):
    specialization_id: str | None
    declared_grade_id: str | None
    verified_specialization_id: str | None = Field(description="Специализация основной категории")
    verified_grade_id: str | None = Field(description="Грейд основной категории")
    viewed_specialization_id: str = Field(description="Специализация, для которой рассчитана доступность")
    viewed_grade_id: str | None = Field(description="Подтверждённый грейд в этой специализации")
    grade_locked_until: datetime | None = Field(description="Блокировка смены грейда в этой специализации")
    upgrade_eligible: bool
    categories: list[Category]
    max_categories: int
    active_attempt: AttemptBrief | None
    eligibility: list[EligibilityOut]
    history: list[ResultBrief]
    rules: TestingRules


class StartIn(BaseModel):
    specialization_id: SpecId
    target_grade: GradeId


class ItemOut(BaseModel):
    id: int
    position: int
    competency_id: str
    competency_name: str
    qtype: str
    text: str
    options: list[str]
    answer: list | None = None


class BlueprintOut(BaseModel):
    specialization: str
    target_grade: str
    length: int
    competency_quota: dict[str, int]
    difficulty_counts: dict[str, int]


class AttemptOut(BaseModel):
    id: int
    specialization_id: str
    target_grade: str
    status: str
    started_at: datetime
    deadline_at: datetime
    server_time: datetime
    answered: int
    total: int
    blueprint: BlueprintOut
    items: list[ItemOut]


class ClientEventsIn(BaseModel):
    """What the test page records, cumulative for the attempt (the candidate is told about it)."""

    focus_lost: int = Field(default=0, ge=0, le=10_000, description="Сколько раз уходил со вкладки теста")
    away_ms: int = Field(default=0, ge=0, le=86_400_000, description="Сколько времени вне вкладки, мс")
    copies: int = Field(default=0, ge=0, le=10_000, description="Копирования текста вопроса")


class AnswerIn(BaseModel):
    attempt_id: int
    item_id: int
    answer: list[int | float | str] = Field(min_length=1, max_length=10)
    time_ms: int | None = Field(default=None, ge=0, le=86_400_000, description="Время на вопросе (видимая вкладка)")
    pasted: bool = Field(default=False, description="Ответ вставлен из буфера обмена")
    client: ClientEventsIn | None = None


class AnswerOut(BaseModel):
    item_id: int
    saved: bool
    answered: int
    total: int


class FinishIn(BaseModel):
    attempt_id: int
    client: ClientEventsIn | None = None


class IntegrityOut(BaseModel):
    level: str = Field(description="ok | attention | risk")
    reasons: list[str] = Field(description="Что замечено, на языке запроса")


class ResultOut(BaseModel):
    attempt_id: int
    specialization_id: str
    target_grade: str
    outcome: str
    passed: bool
    verified_grade: str | None
    category_label: str | None
    scaled_score: int
    raw_percent: float
    theta: float
    theta_se: float
    confidence: float
    competencies: list[CompetencyScore]
    recommendation: str
    grade_changed: bool
    grade_change_blocked: bool
    upgrade_eligible: bool
    answered: int
    total: int
    created_at: datetime
    integrity: IntegrityOut | None = None
