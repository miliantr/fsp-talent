from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.candidate import CandidateProfileOut, LastResult, Step
from app.schemas.common import Company, Contacts
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


class CandidateDashboard(BaseModel):
    profile: CandidateProfileOut
    invitations: InvitationCounters
    last_result: LastResult | None
    steps: list[Step]
    searchable: bool


class TaskIn(BaseModel):
    specialization_id: Literal["backend", "frontend", "data_ml", "devops"]
    title: str = Field(min_length=3, max_length=128)
    description: str = Field(min_length=10, max_length=4000)


class MySubmission(BaseModel):
    id: int
    answer: str
    rating: int | None
    reviewer_comment: str | None
    created_at: datetime


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    specialization_id: str
    specialization_name: str
    is_active: bool
    created_at: datetime
    company: Company
    submissions: int
    my_submission: MySubmission | None


class SubmissionIn(BaseModel):
    answer: str = Field(min_length=20, max_length=6000)


class SubmissionOut(BaseModel):
    id: int
    answer: str
    rating: int | None
    reviewer_comment: str | None
    created_at: datetime
    candidate_id: int
    candidate_name: str


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
