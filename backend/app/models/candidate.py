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
from app.models.reference import Grade, Skill, Specialization
from app.models.user import User


class WorkFormat:
    REMOTE = "remote"
    OFFICE = "office"
    HYBRID = "hybrid"
    ANY = "any"
    ALL = (REMOTE, OFFICE, HYBRID, ANY)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        CheckConstraint("expected_salary IS NULL OR expected_salary > 0", name="salary_positive"),
        CheckConstraint("experience_years >= 0", name="experience_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # --- personal & contacts (private until contact is unlocked) ---
    first_name: Mapped[str] = mapped_column(String(64), default="")
    last_name: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str | None] = mapped_column(String(32))
    telegram: Mapped[str | None] = mapped_column(String(64))
    city: Mapped[str | None] = mapped_column(String(64))

    # --- CV ---
    headline: Mapped[str] = mapped_column(String(120), default="")
    about: Mapped[str] = mapped_column(Text, default="")
    experience_years: Mapped[float] = mapped_column(Float, default=0)
    education: Mapped[str | None] = mapped_column(String(255))
    team_roles: Mapped[list] = mapped_column(JSON, default=list)
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    expected_salary: Mapped[int | None] = mapped_column(Integer)
    work_format: Mapped[str] = mapped_column(String(16), default=WorkFormat.ANY)

    # --- survey: self-declared ---
    specialization_id: Mapped[str | None] = mapped_column(ForeignKey("specializations.id"))
    declared_grade_id: Mapped[str | None] = mapped_column(ForeignKey("grades.id"))

    # --- verified by the testing engine (the only source of the category) ---
    # A candidate may hold one category per specialization (candidate_categories); the columns below
    # mirror the PRIMARY category, so screens that show "the" category read them directly.
    verified_grade_id: Mapped[str | None] = mapped_column(ForeignKey("grades.id"), index=True)
    verified_specialization_id: Mapped[str | None] = mapped_column(
        ForeignKey("specializations.id"), index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    grade_locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    upgrade_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    ability_theta: Mapped[float | None] = mapped_column(Float)
    scaled_score: Mapped[int | None] = mapped_column(Integer)
    category_confidence: Mapped[float | None] = mapped_column(Float)
    competency_scores: Mapped[dict] = mapped_column(JSON, default=dict)

    # --- privacy & consents (152-FZ) ---
    open_to_offers: Mapped[bool] = mapped_column(Boolean, default=True)
    # the full name and the work history may be shown before contact (client clarification): only the
    # contacts are closed; a candidate can still hide the last name
    show_full_name: Mapped[bool] = mapped_column(Boolean, default=True)
    show_fsp: Mapped[bool] = mapped_column(Boolean, default=True)
    show_salary: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_processing_at: Mapped[datetime | None] = mapped_column(DateTime)
    consent_publication_at: Mapped[datetime | None] = mapped_column(DateTime)

    fsp_id: Mapped[str | None] = mapped_column(String(32), unique=True)
    # pending FSP ID ownership confirmation (code sent to the e-mail registered in FSP)
    fsp_pending_id: Mapped[str | None] = mapped_column(String(32))
    fsp_code_hash: Mapped[str | None] = mapped_column(String(64))
    fsp_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    resume_filename: Mapped[str | None] = mapped_column(String(255))

    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    profile_updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship()
    specialization: Mapped[Specialization | None] = relationship(foreign_keys=[specialization_id])
    verified_specialization: Mapped[Specialization | None] = relationship(
        foreign_keys=[verified_specialization_id]
    )
    declared_grade: Mapped[Grade | None] = relationship(foreign_keys=[declared_grade_id])
    verified_grade: Mapped[Grade | None] = relationship(foreign_keys=[verified_grade_id])
    skills: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )
    task_submissions: Mapped[list["TaskSubmission"]] = relationship(  # noqa: F821
        back_populates="candidate", viewonly=True
    )
    categories: Mapped[list["CandidateCategory"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", lazy="selectin",
        order_by="(CandidateCategory.is_primary.desc(), CandidateCategory.verified_at)",
    )
    fsp_profile: Mapped["FSPProfile | None"] = relationship(  # noqa: F821
        back_populates="candidate", cascade="all, delete-orphan", uselist=False
    )

    @property
    def is_verified(self) -> bool:
        return self.verified_grade_id is not None and self.verified_specialization_id is not None

    @property
    def is_searchable(self) -> bool:
        return (
            self.is_verified
            and self.open_to_offers
            and self.consent_publication_at is not None
            and self.user.is_active
        )


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
        CheckConstraint("level BETWEEN 1 AND 5", name="level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    level: Mapped[int] = mapped_column(Integer, default=3)
    years: Mapped[float] = mapped_column(Float, default=1)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship()


class CandidateCategory(Base):
    """A verified category «specialization · grade». One per specialization; exactly one is primary.

    Only the testing engine writes here: a passed test creates or updates the category of its
    specialization, the grade-change lock and the fast track are kept per category."""

    __tablename__ = "candidate_categories"
    __table_args__ = (UniqueConstraint("candidate_id", "specialization_id", name="uq_candidate_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    specialization_id: Mapped[str] = mapped_column(ForeignKey("specializations.id"), index=True)
    grade_id: Mapped[str] = mapped_column(ForeignKey("grades.id"), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    theta: Mapped[float] = mapped_column(Float, default=0)
    scaled_score: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    competency_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    verified_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    grade_locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    upgrade_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    candidate: Mapped[CandidateProfile] = relationship(back_populates="categories")
