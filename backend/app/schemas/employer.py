from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.common import (
    CandidateSkillView,
    Category,
    Company,
    CompetencyScore,
    Contacts,
    FSPProfileView,
    FSPSummaryView,
    GradeId,
    SpecId,
    WorkFormatT,
)


class CompanyIn(BaseModel):
    company_name: str | None = Field(default=None, max_length=128)
    industry: str | None = Field(default=None, max_length=96)
    description: str | None = Field(default=None, max_length=4000)
    website: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=64)
    size: str | None = Field(default=None, max_length=32)
    contact_name: str | None = Field(default=None, max_length=128)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=32)
    contact_telegram: str | None = Field(default=None, max_length=64)


class CompanyOut(BaseModel):
    id: int
    email: str
    company_name: str
    industry: str
    description: str
    website: str | None
    city: str | None
    size: str | None
    contact_name: str | None
    contact_email: str | None
    contact_phone: str | None
    contact_telegram: str | None


class RequirementIn(BaseModel):
    title: str = Field(min_length=3, max_length=128)
    description: str = Field(default="", max_length=6000)
    team_description: str = Field(default="", max_length=4000)
    specialization_id: SpecId
    grade_id: GradeId
    must_skills: list[str] = Field(default_factory=list, max_length=15)
    nice_skills: list[str] = Field(default_factory=list, max_length=15)
    salary_from: int = Field(gt=0, le=10_000_000, description="Обязательно, ₽")
    salary_to: int = Field(gt=0, le=10_000_000, description="Обязательно, ₽")
    work_format: WorkFormatT = "any"
    city: str | None = Field(default=None, max_length=64)
    min_experience_years: float = Field(default=0, ge=0, le=30)
    weights_preset: Literal["balanced", "skills_first", "proven_talent"] = "balanced"
    is_public: bool = False

    @model_validator(mode="after")
    def _salary(self):
        if self.salary_to < self.salary_from:
            raise PydanticCustomError("salary_range", "salary_to must not be less than salary_from")
        return self


class JobSkillOut(BaseModel):
    slug: str
    name: str
    importance: str


class JobStats(BaseModel):
    matched: int
    shortlisted: int
    invited: int
    accepted: int
    applications: int
    top_percent: int | None


class RequirementOut(BaseModel):
    id: int
    title: str
    description: str
    team_description: str
    specialization_id: str
    specialization_name: str
    grade_id: str
    grade_name: str
    salary_from: int
    salary_to: int
    work_format: str
    city: str | None
    min_experience_years: float
    weights_preset: str
    is_public: bool
    status: str
    created_at: datetime
    updated_at: datetime
    matched_at: datetime | None
    skills: list[JobSkillOut]
    company: Company
    stats: JobStats | None = None


class ParseNeedIn(BaseModel):
    text: str = Field(min_length=10, max_length=6000)


class SkillRefOut(BaseModel):
    slug: str
    name: str


class ParsedSkillOut(SkillRefOut):
    importance: Literal["must", "nice"] = "must"


class ParseNeedOut(BaseModel):
    specialization_id: str | None
    grade_id: str | None
    skills: list[ParsedSkillOut]  # must-have first; "желательно X" / "X будет плюсом" -> nice
    salary_from: int | None
    salary_to: int | None
    work_format: str | None
    min_experience_years: float | None


# ------------------------------------------------------------------ matching

class ComponentOut(BaseModel):
    key: str
    label: str
    value: float
    weight: float
    available: bool
    detail: str
    contribution: float


class ReasonOut(BaseModel):
    kind: Literal["positive", "neutral", "negative"]
    component: str
    text: str


class SkillMatchOut(BaseModel):
    skill: str
    name: str
    importance: str
    status: Literal["exact", "related", "missing"]
    via: str | None
    verified: bool
    value: float


class MatchOut(BaseModel):
    percent: int
    rank: int | None = None
    score: float
    components: list[ComponentOut]
    reasons: list[ReasonOut]
    skill_matches: list[SkillMatchOut]
    must_gate: float = Field(default=1.0, description="Множитель за покрытие обязательных навыков")


class CandidateCard(BaseModel):
    candidate_id: int
    display_name: str
    headline: str
    city: str | None
    experience_years: float
    work_format: str
    expected_salary: int | None
    category: Category | None
    skills: list[CandidateSkillView]
    fsp: FSPSummaryView
    last_active_days: int | None
    match: MatchOut | None = None
    shortlisted: bool = False
    invitation_status: str | None = None
    applied: bool = False
    profile_strength: int | None = None


class CategoryGroup(BaseModel):
    label: str
    specialization_id: str
    grade_id: str
    count: int
    avg_percent: int
    top_percent: int


class WeightOut(BaseModel):
    key: str
    label: str
    weight: float


class MatchListOut(BaseModel):
    requirement: RequirementOut
    total: int
    filtered: int
    items: list[CandidateCard]
    categories: list[CategoryGroup]
    computed_at: datetime | None
    engine_version: str
    weights: list[WeightOut]


class CategoryCount(BaseModel):
    label: str
    count: int


class BankOut(BaseModel):
    total: int
    items: list[CandidateCard]
    categories: list[CategoryCount]


class CompareSide(BaseModel):
    candidate_id: int
    percent: int
    components: list[ComponentOut]


class CompareDelta(BaseModel):
    key: str
    label: str
    delta: float


class CompareOut(BaseModel):
    delta_percent: int
    components: list[CompareDelta]
    summary: str
    a: CompareSide
    b: CompareSide


class TestHistoryItem(BaseModel):
    attempt_id: int
    target_grade: str
    specialization_id: str
    outcome: str
    scaled_score: int
    created_at: datetime


class InvitationCandidate(BaseModel):
    id: int
    display_name: str
    category_label: str | None


class InvitationOut(BaseModel):
    id: int
    status: str
    created_at: datetime
    viewed_at: datetime | None
    responded_at: datetime | None
    expires_at: datetime
    position_title: str
    description: str
    salary_from: int
    salary_to: int
    work_format: str
    contact_method: str
    match_score: float | None
    match_reasons: list[ReasonOut]
    candidate_message: str | None
    job_id: int | None
    job_title: str | None
    company: Company
    candidate: InvitationCandidate
    contacts: Contacts | None


class CandidateDetail(CandidateCard):
    about: str
    education: str | None
    team_roles: list[str]
    soft_skills: list[str]
    competencies: list[CompetencyScore]
    test_history: list[TestHistoryItem]
    fsp_profile: FSPProfileView | None
    contacts_visible: bool
    contacts_reason: str | None
    contacts: Contacts | None
    invitations: list[InvitationOut]
    requirement_id: int | None


class InvitationIn(BaseModel):
    candidate_id: int
    job_id: int | None = None
    position_title: str = Field(min_length=3, max_length=128)
    description: str = Field(min_length=10, max_length=4000)
    salary_from: int = Field(gt=0, le=10_000_000, description="Обязательно, ₽")
    salary_to: int = Field(gt=0, le=10_000_000, description="Обязательно, ₽")
    work_format: WorkFormatT = "any"
    contact_method: str = Field(min_length=3, max_length=255, description="Как связаться с работодателем")

    @model_validator(mode="after")
    def _salary(self):
        if self.salary_to < self.salary_from:
            raise PydanticCustomError("salary_range", "salary_to must not be less than salary_from")
        return self


class RespondIn(BaseModel):
    message: str | None = Field(default=None, max_length=2000)


class ReportIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class EmployerInvitationStats(BaseModel):
    total: int
    by_status: dict[str, int]
    acceptance_rate: int | None


class EmployerDashboard(BaseModel):
    company: CompanyOut
    company_complete: bool
    requirements: list[RequirementOut]
    requirements_total: int
    invitations: EmployerInvitationStats
    recent_responses: list[InvitationOut]
