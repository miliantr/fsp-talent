from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

GradeId = Literal["junior", "middle", "senior"]
SpecId = Literal["backend", "frontend", "data_ml", "devops"]
WorkFormatT = Literal["remote", "office", "hybrid", "any"]


class ApiError(BaseModel):
    code: str
    message: str
    details: dict = {}


class Message(BaseModel):
    message: str


class Company(BaseModel):
    id: int
    name: str
    industry: str | None = None
    city: str | None = None
    website: str | None = None
    description: str | None = None
    size: str | None = None


class Category(BaseModel):
    label: str
    specialization_id: str
    specialization_name: str
    grade_id: str
    grade_name: str
    verified_at: datetime | None
    scaled_score: int | None
    confidence: float | None
    theta: float | None
    locked_until: datetime | None
    upgrade_eligible: bool


class CandidateSkillView(BaseModel):
    slug: str
    name: str
    level: int
    years: float
    verified: bool
    competency_score: int | None = None


class CompetencyScore(BaseModel):
    id: str
    name: str
    score: int


class FSPSummaryView(BaseModel):
    available: bool
    strength: float
    count: int
    prizes: int
    best_text: str | None = None
    sport_rank: str | None = None
    highlights: list[str] = []


class FSPAchievementView(BaseModel):
    id: str
    event_name: str
    discipline: str
    level: str
    level_name: str
    date: date
    place: int | None = None
    participants_total: int | None = None
    team_name: str | None = None
    role: str | None = None
    score: float | None = None
    certificate_url: str | None = None


class FSPProfileView(BaseModel):
    fsp_id: str
    full_name: str
    region: str | None = None
    sport_rank: str | None = None
    source: str
    synced_at: datetime
    achievements: list[FSPAchievementView]


class Contacts(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    telegram: str | None = None


class SalaryRange(BaseModel):
    salary_from: int = Field(gt=0, le=10_000_000, description="Нижняя граница, ₽")
    salary_to: int = Field(gt=0, le=10_000_000, description="Верхняя граница, ₽")
