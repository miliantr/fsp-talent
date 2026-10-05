from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, Unauthorized, ValidationFailed
from app.core.security import (
    create_access_token,
    hash_code,
    hash_password,
    new_email_code,
    verify_password,
)
from app.db.base import utcnow
from app.models import CandidateProfile, EmployerProfile, Role, User
from app.services import fsp_service
from app.services.mailer import send_email


def _issue_code(user: User) -> str:
    code = new_email_code()
    user.email_code_hash = hash_code(code)
    user.email_code_expires_at = utcnow() + timedelta(minutes=get_settings().email_code_ttl_minutes)
    send_email(
        user.email,
        "Подтверждение e-mail — FSP Talent",
        f"Ваш код подтверждения: {code}\nКод действует {get_settings().email_code_ttl_minutes} минут.",
    )
    return code


def register(db: Session, email: str, password: str, role: str, consent: bool,
             first_name: str = "", last_name: str = "", company_name: str = "") -> tuple[User, str | None]:
    if role not in Role.ALL:
        raise ValidationFailed("Неизвестная роль")
    if not consent:
        raise ValidationFailed("Необходимо согласие на обработку персональных данных (152-ФЗ)")
    email = email.strip().lower()
    if db.query(User).filter_by(email=email).first():
        raise Conflict("Пользователь с таким e-mail уже зарегистрирован", code="email_taken")
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.flush()
    if role == Role.CANDIDATE:
        db.add(CandidateProfile(user_id=user.id, first_name=first_name.strip(), last_name=last_name.strip(),
                                consent_processing_at=utcnow()))
    else:
        db.add(EmployerProfile(user_id=user.id, company_name=company_name.strip(), contact_email=email))
    code = _issue_code(user)
    db.commit()
    return user, code if get_settings().email_dev_expose_code else None


def resend_code(db: Session, email: str) -> str | None:
    user = db.query(User).filter_by(email=email.strip().lower()).first()
    if not user or user.is_email_verified:
        return None  # do not reveal whether the address exists
    code = _issue_code(user)
    db.commit()
    return code if get_settings().email_dev_expose_code else None


def verify_email(db: Session, email: str, code: str) -> User:
    user = db.query(User).filter_by(email=email.strip().lower()).first()
    if not user:
        raise ValidationFailed("Неверный код подтверждения")
    if user.is_email_verified:
        return user
    if not user.email_code_hash or not user.email_code_expires_at or utcnow() > user.email_code_expires_at:
        raise ValidationFailed("Код истёк — запросите новый", code="code_expired")
    if hash_code(code.strip()) != user.email_code_hash:
        raise ValidationFailed("Неверный код подтверждения", code="code_invalid")
    user.is_email_verified = True
    user.email_code_hash = None
    user.last_login_at = utcnow()
    if user.role == Role.CANDIDATE:
        profile = db.query(CandidateProfile).filter_by(user_id=user.id).one()
        # automatic enrichment: the verified e-mail is matched against the FSP registry
        fsp_service.try_auto_link(db, profile)
    db.commit()
    return user


def login(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter_by(email=email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        raise Unauthorized("Неверный e-mail или пароль", code="invalid_credentials")
    if not user.is_active:
        raise Forbidden("Учётная запись заблокирована")
    if not user.is_email_verified:
        raise Forbidden("Подтвердите e-mail — код отправлен на почту", code="email_not_verified")
    user.last_login_at = utcnow()
    if user.role == Role.CANDIDATE:
        profile = db.query(CandidateProfile).filter_by(user_id=user.id).one_or_none()
        if profile:
            profile.last_active_at = utcnow()
    db.commit()
    return user


def token_for(user: User) -> str:
    return create_access_token(user.id, user.email, user.role)
