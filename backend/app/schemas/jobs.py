from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.candidate import CandidateProfileOut, LastResult, Step
from app.schemas.common import Company, Contacts, GradeId
from app.schemas.employer import CandidateCard, InvitationOut, RequirementOut


class PublicJobOut(RequirementOut):
    application_status: str | None = None
    match_percent: int | None = None


class ApplicationIn(BaseModel):
    job_id: int
    cover_letter: str = Field(default="", max_length=3000)


class ApplicationOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    cover_letter: str
    match_percent: int | None
    job: RequirementOut


class ApplicationJobRef(BaseModel):
    id: int
    title: str


class EmployerApplicationOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    cover_letter: str
    match_percent: int | None
    job: ApplicationJobRef
    candidate: CandidateCard
    contacts: Contacts


class ApplicationStatusIn(BaseModel):
    status: Literal["viewed", "accepted", "rejected"]


class InvitationCounters(BaseModel):
    total: int
    new: int
    active: int
    accepted: int
    latest: list[InvitationOut]


# ------------------------------------------------------------------ regular tasks

class AnswerSpec(BaseModel):
    """Key of an auto-checked task: a number (± tolerance) or accepted short texts."""

    kind: Literal["number", "text"]
    value: float | None = None
    tolerance: float = Field(default=0, ge=0)
    accepted: list[str] = Field(default=[], max_length=10)


class TaskIn(BaseModel):
    specialization_id: Literal["backend", "frontend", "data_ml", "devops"]
    title: str = Field(min_length=3, max_length=128)
    description: str = Field(min_length=10, max_length=4000)
    mode: Literal["solve", "approach"] = Field(
        default="approach", description="solve — ответ проверяется автоматически; approach — подход, рубрика")
    audience: Literal["targeted", "category"] = Field(
        default="targeted", description="targeted — система предлагает адресно; category — челлендж категории")
    grade_id: GradeId | None = Field(default=None, description="Грейд, на который рассчитано задание")
    job_id: int | None = Field(default=None, description="Потребность, к которой относится задание")
    competency_id: str | None = Field(default=None, max_length=32, description="Проверяемая компетенция")
    answer_spec: AnswerSpec | None = None
    key_points: list[str] = Field(default=[], max_length=8, description="Ключевые идеи хорошего ответа")
    time_limit_days: int = Field(default=7, ge=1, le=30)
    max_offers: int = Field(default=20, ge=1, le=200, description="Сколько кандидатам предложить адресно")


class TaskActiveIn(BaseModel):
    is_active: bool


class TaskView(BaseModel):
    id: int
    title: str
    description: str
    mode: str
    audience: str
    answer_kind: str | None = Field(description="number | text для задач с автопроверкой")
    specialization_id: str
    specialization_name: str
    grade_id: str | None
    grade_name: str | None
    competency_id: str | None
    competency_name: str | None
    requirement_title: str | None
    time_limit_days: int
    is_active: bool
    created_at: datetime
    company: Company


class TaskStats(BaseModel):
    offered: int
    submitted: int
    pending_review: int
    avg_score: int | None


class EmployerTaskOut(TaskView):
    job_id: int | None
    answer_spec: dict | None
    key_points: list[str]
    max_offers: int
    stats: TaskStats


class TaskOfferOut(BaseModel):
    assignment_id: int
    source: str = Field(description="system — подобрано системой, employer — лично от работодателя")
    reasons: list[str]
    offered_at: datetime
    due_at: datetime
    task: TaskView


class TaskResultOut(BaseModel):
    """The candidate's own result: the auto-check verdict or the employer's rubric (never the key)."""

    id: int
    task_id: int
    task_title: str
    mode: str
    company: Company
    answer: str
    status: str
    correct: bool | None
    rubric: dict[str, int] | None
    score: int | None
    reviewer_comment: str | None
    created_at: datetime
    reviewed_at: datetime | None


class CandidateTasksOut(BaseModel):
    offered: list[TaskOfferOut]
    challenges: list[TaskView]
    history: list[TaskResultOut]
    next_offer_at: datetime | None
    interval_days: int
    verified: bool


class CandidateDashboard(BaseModel):
    profile: CandidateProfileOut
    invitations: InvitationCounters
    last_result: LastResult | None
    steps: list[Step]
    searchable: bool
    task_offer: TaskOfferOut | None = None


class SubmissionIn(BaseModel):
    answer: str = Field(min_length=1, max_length=6000)


class SubmissionOut(BaseModel):
    id: int
    answer: str
    status: str
    auto_score: float | None = Field(description="Автопроверка (1/0) или доля ключевых идей — предварительно")
    auto_detail: dict | None
    rubric: dict[str, int] | None
    score: int | None
    rating: int | None
    reviewer_comment: str | None
    created_at: datetime
    candidate_id: int
    candidate_name: str
    category_label: str | None


class Rubric(BaseModel):
    correctness: int = Field(ge=0, le=2, description="Решение верно и применимо")
    completeness: int = Field(ge=0, le=2, description="Учтены крайние случаи и ограничения")
    reasoning: int = Field(ge=0, le=2, description="Обоснованы компромиссы")


class ReviewIn(BaseModel):
    rubric: Rubric
    comment: str | None = Field(default=None, max_length=2000)


class OfferTaskIn(BaseModel):
    candidate_id: int
