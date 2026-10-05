"""Employer needs (requirements / vacancies), match snapshots, invitations, applications, tasks."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow
from app.models.candidate import CandidateProfile
from app.models.employer import EmployerProfile
from app.models.reference import Skill


class Job(Base):
    """A described need of an employer.

    Private by default (a "requirement" that drives the matching engine). When `is_public` is set it
    is also listed on the job board and candidates can apply on their own.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("salary_from > 0 AND salary_to >= salary_from", name="salary_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    team_description: Mapped[str] = mapped_column(Text, default="")
    specialization_id: Mapped[str] = mapped_column(ForeignKey("specializations.id"), index=True)
    grade_id: Mapped[str] = mapped_column(ForeignKey("grades.id"))
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    work_format: Mapped[str] = mapped_column(String(16), default="any")
    city: Mapped[str | None] = mapped_column(String(64))
    min_experience_years: Mapped[float] = mapped_column(Float, default=0)
    weights_preset: Mapped[str] = mapped_column(String(24), default="balanced")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    matched_at: Mapped[datetime | None] = mapped_column(DateTime)

    employer: Mapped[EmployerProfile] = relationship()
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    importance: Mapped[str] = mapped_column(String(8), default="must")  # must | nice

    job: Mapped[Job] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


class MatchResult(Base):
    """Persisted ranking snapshot: lets the employer filter/refine without losing the selection."""

    __tablename__ = "match_results"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_match_job_candidate"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)
    rank: Mapped[int] = mapped_column(Integer)
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[list] = mapped_column(JSON, default=list)
    engine_version: Mapped[str] = mapped_column(String(16))
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    candidate: Mapped[CandidateProfile] = relationship()


class InvitationStatus:
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    ACTIVE = (SENT, VIEWED)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        CheckConstraint("salary_from > 0 AND salary_to >= salary_from", name="salary_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"))
    position_title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    work_format: Mapped[str] = mapped_column(String(16), default="any")
    contact_method: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default=InvitationStatus.SENT, index=True)
    match_score: Mapped[float | None] = mapped_column(Float)
    match_reasons: Mapped[list] = mapped_column(JSON, default=list)
    candidate_message: Mapped[str | None] = mapped_column(Text)
    reported: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    employer: Mapped[EmployerProfile] = relationship()
    candidate: Mapped[CandidateProfile] = relationship()
    job: Mapped[Job | None] = relationship()


class ApplicationStatus:
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ALL = (SENT, VIEWED, ACCEPTED, REJECTED)


class Application(Base):
    """Candidate-initiated response to a public vacancy (secondary scenario)."""

    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_application"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default=ApplicationStatus.SENT)
    match_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    job: Mapped[Job] = relationship()
    candidate: Mapped[CandidateProfile] = relationship()


class ContactAccessLog(Base):
    """Audit trail of every disclosure of candidate contacts to an employer (152-FZ)."""

    __tablename__ = "contact_access_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profiles.id", ondelete="CASCADE"))
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE")
    )
    reason: Mapped[str] = mapped_column(String(32))  # invitation_accepted | application
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ShortTask(Base):
    """Regular short task from an employer: keeps candidate profiles fresh."""

    __tablename__ = "short_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"), index=True
    )
    specialization_id: Mapped[str] = mapped_column(ForeignKey("specializations.id"))
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    employer: Mapped[EmployerProfile] = relationship()


class TaskSubmission(Base):
    __tablename__ = "task_submissions"
    __table_args__ = (
        UniqueConstraint("task_id", "candidate_id", name="uq_task_submission"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("short_tasks.id", ondelete="CASCADE"))
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    answer: Mapped[str] = mapped_column(Text)
    rating: Mapped[int | None] = mapped_column(Integer)
    reviewer_comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    task: Mapped[ShortTask] = relationship()
    candidate: Mapped[CandidateProfile] = relationship()
