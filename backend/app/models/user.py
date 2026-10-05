from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class Role:
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ALL = (CANDIDATE, EMPLOYER)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_code_hash: Mapped[str | None] = mapped_column(String(255))
    email_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Subject in an external IdP (FSP ID / Keycloak). Allows linking accounts later without migration.
    external_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    # preferred interface language (ru | en): restored on sign-in from any device
    locale: Mapped[str] = mapped_column(String(8), default="ru", server_default="ru")
