"""Question bank, generated test forms (attempts), answers and results."""

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


class QuestionType:
    SINGLE = "single"
    MULTI = "multi"
    NUMERIC = "numeric"
    ALL = (SINGLE, MULTI, NUMERIC)


class Question(Base):
    """A calibrated item of the bank.

    `family` is set for parametric item templates: every time the item is drawn the generator
    renders a fresh isomorphic variant (different numbers, same difficulty), so a leaked copy of
    the answer is useless for the next candidate.
    """

    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_question_code_version"),
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="difficulty_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    specialization_id: Mapped[str] = mapped_column(ForeignKey("specializations.id"), index=True)
    competency_id: Mapped[str] = mapped_column(ForeignKey("competencies.id"), index=True)
    difficulty: Mapped[int] = mapped_column(Integer)
    qtype: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct: Mapped[list] = mapped_column(JSON, default=list)  # indices into options / [number]
    explanation: Mapped[str] = mapped_column(Text, default="")
    family: Mapped[str | None] = mapped_column(String(48))
    # IRT (3PL) parameters: discrimination a, difficulty b, pseudo-guessing c.
    irt_a: Mapped[float] = mapped_column(Float, default=1.0)
    irt_b: Mapped[float] = mapped_column(Float, default=0.0)
    irt_c: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    exposure_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AttemptStatus:
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    EXPIRED = "expired"


class TestAttempt(Base):
    """One generated test form for one candidate (the "Test" entity)."""

    __tablename__ = "test_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    specialization_id: Mapped[str] = mapped_column(ForeignKey("specializations.id"))
    target_grade_id: Mapped[str] = mapped_column(ForeignKey("grades.id"))
    status: Mapped[str] = mapped_column(String(16), default=AttemptStatus.IN_PROGRESS, index=True)
    seed: Mapped[int] = mapped_column(Integer)
    blueprint: Mapped[dict] = mapped_column(JSON, default=dict)
    form_mean_b: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    deadline_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    items: Mapped[list["TestItem"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", order_by="TestItem.position"
    )
    result: Mapped["TestResult | None"] = relationship(
        back_populates="attempt", cascade="all, delete-orphan", uselist=False
    )


class TestItem(Base):
    """A rendered question inside an attempt (shuffled options, instantiated parameters)."""

    __tablename__ = "test_items"
    __table_args__ = (UniqueConstraint("attempt_id", "position", name="uq_item_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("test_attempts.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    position: Mapped[int] = mapped_column(Integer)
    competency_id: Mapped[str] = mapped_column(String(32))
    difficulty: Mapped[int] = mapped_column(Integer)
    qtype: Mapped[str] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text)
    options: Mapped[list] = mapped_column(JSON, default=list)
    correct: Mapped[list] = mapped_column(JSON, default=list)  # never sent to the client
    irt_a: Mapped[float] = mapped_column(Float)
    irt_b: Mapped[float] = mapped_column(Float)
    irt_c: Mapped[float] = mapped_column(Float)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    family: Mapped[str | None] = mapped_column(String(48))

    attempt: Mapped[TestAttempt] = relationship(back_populates="items")
    answer: Mapped["TestAnswer | None"] = relationship(
        back_populates="item", cascade="all, delete-orphan", uselist=False
    )


class TestAnswer(Base):
    __tablename__ = "test_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("test_items.id", ondelete="CASCADE"), unique=True
    )
    answer: Mapped[list] = mapped_column(JSON, default=list)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    credit: Mapped[float] = mapped_column(Float, default=0)
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    item: Mapped[TestItem] = relationship(back_populates="answer")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("test_attempts.id", ondelete="CASCADE"), unique=True
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), index=True
    )
    theta: Mapped[float] = mapped_column(Float)
    theta_se: Mapped[float] = mapped_column(Float)
    scaled_score: Mapped[int] = mapped_column(Integer)
    raw_percent: Mapped[float] = mapped_column(Float)
    outcome: Mapped[str] = mapped_column(String(32))  # passed | passed_upgrade | not_passed
    passed: Mapped[bool] = mapped_column(Boolean)
    confidence: Mapped[float] = mapped_column(Float)
    verified_grade_id: Mapped[str | None] = mapped_column(ForeignKey("grades.id"))
    grade_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    grade_change_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    # leakage detector: person-fit (lz*) and ability gap between leak-prone and leak-proof items
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    person_fit: Mapped[float | None] = mapped_column(Float)
    leak_z: Mapped[float | None] = mapped_column(Float)
    category_label: Mapped[str | None] = mapped_column(String(64))
    competency_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    attempt: Mapped[TestAttempt] = relationship(back_populates="result")
