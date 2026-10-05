"""Local snapshot of the candidate's data from the FSP registry (synced through FSPRegistry)."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class FSPProfile(Base):
    __tablename__ = "fsp_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), unique=True
    )
    fsp_id: Mapped[str] = mapped_column(String(32), index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    region: Mapped[str | None] = mapped_column(String(96))
    sport_rank: Mapped[str | None] = mapped_column(String(48))  # спортивный разряд
    source: Mapped[str] = mapped_column(String(16), default="mock")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    candidate = relationship("CandidateProfile", back_populates="fsp_profile")
    achievements: Mapped[list["FSPAchievement"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", order_by="FSPAchievement.date.desc()"
    )


class FSPAchievement(Base):
    __tablename__ = "fsp_achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("fsp_profiles.id", ondelete="CASCADE"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(48))
    event_name: Mapped[str] = mapped_column(String(160))
    discipline: Mapped[str] = mapped_column(String(64))
    level: Mapped[str] = mapped_column(String(24))  # regional | federal | all_russian | international
    date: Mapped[date] = mapped_column(Date)
    place: Mapped[int | None] = mapped_column(Integer)
    participants_total: Mapped[int | None] = mapped_column(Integer)
    team_name: Mapped[str | None] = mapped_column(String(96))
    role: Mapped[str | None] = mapped_column(String(48))
    score: Mapped[float | None] = mapped_column(Float)
    specialization_hint: Mapped[str | None] = mapped_column(String(32))
    certificate_url: Mapped[str | None] = mapped_column(String(255))

    profile: Mapped[FSPProfile] = relationship(back_populates="achievements")
