from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow
from app.models.user import User


class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str] = mapped_column(String(128), default="")
    industry: Mapped[str] = mapped_column(String(96), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(64))
    size: Mapped[str | None] = mapped_column(String(32))
    contact_name: Mapped[str | None] = mapped_column(String(128))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_telegram: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship()
