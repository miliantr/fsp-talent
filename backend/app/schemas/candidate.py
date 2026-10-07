from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import (
    CandidateSkillView,
    Category,
    CompetencyScore,
    FSPProfileView,
    FSPSummaryView,
    GradeId,
    GradeStatus,
    SpecId,
    WorkFormatT,
)


class CandidateSkillIn(BaseModel):
    slug: str = Field(max_length=48)
    level: int = Field(ge=1, le=5)
    years: float = Field(ge=0, le=50)


class CandidateProfileIn(BaseModel):
    first_name: str | None = Field(default=None, max_length=64)
    last_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    telegram: str | None = Field(default=None, max_length=64)
    city: str | None = Field(default=None, max_length=64)
    headline: str | None = Field(default=None, max_length=120)
    about: str | None = Field(default=None, max_length=4000)
    experience_years: float | None = Field(default=None, ge=0, le=50)
    education: str | None = Field(default=None, max_length=255)
    team_roles: list[str] | None = Field(default=None, max_length=10)
    soft_skills: list[str] | None = Field(default=None, max_length=15)
    expected_salary: int | None = Field(default=None, gt=0, le=10_000_000)
    work_format: WorkFormatT | None = None
    specialization_id: SpecId | None = None
    declared_grade_id: GradeId | None = None
    skills: list[CandidateSkillIn] | None = None


class CompletenessItem(BaseModel):
    key: str
    title: str


class Completeness(BaseModel):
    percent: int
    missing: list[CompletenessItem]


class CandidateSettings(BaseModel):
    open_to_offers: bool
    show_full_name: bool
    show_fsp: bool
    show_salary: bool
    consent_processing_at: datetime | None
    consent_publication_at: datetime | None
    searchable: bool


class CandidateSettingsIn(BaseModel):
    open_to_offers: bool | None = None
    show_full_name: bool | None = None
    show_fsp: bool | None = None
    show_salary: bool | None = None
    consent_publication: bool | None = None


class CandidateProfileOut(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None
    telegram: str | None
    city: str | None
    headline: str
    about: str
    experience_years: float
    education: str | None
    team_roles: list[str]
    soft_skills: list[str]
    expected_salary: int | None
    work_format: str
    specialization_id: str | None
    declared_grade_id: str | None
    skills: list[CandidateSkillView]
    category: Category | None = Field(description="Основная категория")
    categories: list[Category] = Field(default=[], description="Все подтверждённые категории, основная первой")
    grade_status: GradeStatus
    competencies: list[CompetencyScore]
    completeness: Completeness
    fsp: FSPSummaryView
    fsp_id: str | None
    settings: CandidateSettings
    resume_filename: str | None
    profile_updated_at: datetime


class SkillRef(BaseModel):
    slug: str
    name: str


class ResumeParseOut(BaseModel):
    filename: str
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    telegram: str | None
    specialization_id: str | None
    declared_grade_id: str | None
    experience_years: float | None
    work_format: str | None
    expected_salary: int | None
    skills: list[SkillRef]
    text_preview: str


class Step(BaseModel):
    key: str
    title: str
    done: bool
    link: str


class LastResult(BaseModel):
    attempt_id: int
    outcome: str
    scaled_score: int
    target_grade: str
    created_at: datetime


class FSPOut(BaseModel):
    linked: bool
    fsp_id: str | None
    pending_fsp_id: str | None
    summary: FSPSummaryView
    profile: FSPProfileView | None


class FSPLinkIn(BaseModel):
    fsp_id: str = Field(min_length=3, max_length=32)


class FSPLinkOut(BaseModel):
    status: str
    masked_email: str | None = None
    dev_code: str | None = None


class FSPConfirmIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
