from fastapi import APIRouter, status

from app.api.deps import DB, CurrentUser
from app.api.responses import errors
from app.models import CandidateProfile, EmployerProfile, Role, User
from app.schemas.auth import (
    LocaleIn,
    LoginIn,
    RegisterIn,
    RegisterOut,
    ResendIn,
    TokenOut,
    UserOut,
    VerifyIn,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


def user_out(db, user: User) -> UserOut:
    name = user.email
    if user.role == Role.CANDIDATE:
        p = db.query(CandidateProfile).filter_by(user_id=user.id).one_or_none()
        if p and p.first_name:
            name = f"{p.first_name} {p.last_name}".strip()
    else:
        e = db.query(EmployerProfile).filter_by(user_id=user.id).one_or_none()
        if e and e.company_name:
            name = e.company_name
    return UserOut(id=user.id, email=user.email, role=user.role, is_email_verified=user.is_email_verified,
                   display_name=name, locale=user.locale or "ru")


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED,
             responses=errors(409, 422), summary="Регистрация по e-mail")
def register(body: RegisterIn, db: DB):
    """Создаёт учётную запись кандидата или работодателя и отправляет 6-значный код подтверждения e-mail."""
    user, code = auth_service.register(db, body.email, body.password, body.role, body.consent_processing,
                                       body.first_name, body.last_name, body.company_name)
    return RegisterOut(email=user.email, dev_code=code)


@router.post("/verify-email", response_model=TokenOut, responses=errors(422), summary="Подтверждение e-mail")
def verify_email(body: VerifyIn, db: DB):
    user = auth_service.verify_email(db, body.email, body.code)
    return TokenOut(access_token=auth_service.token_for(user), user=user_out(db, user))


@router.post("/resend-code", response_model=RegisterOut, summary="Повторная отправка кода")
def resend_code(body: ResendIn, db: DB):
    return RegisterOut(email=body.email, dev_code=auth_service.resend_code(db, body.email))


@router.post("/login", response_model=TokenOut, responses=errors(401, 403), summary="Вход")
def login(body: LoginIn, db: DB):
    user = auth_service.login(db, body.email, body.password)
    return TokenOut(access_token=auth_service.token_for(user), user=user_out(db, user))


@router.get("/me", response_model=UserOut, responses=errors(401), summary="Текущий пользователь")
def me(user: CurrentUser, db: DB):
    return user_out(db, user)


@router.put("/me/locale", response_model=UserOut, responses=errors(401, 422), summary="Сменить язык интерфейса")
def set_locale(body: LocaleIn, user: CurrentUser, db: DB):
    """Сохраняет выбранный язык в учётной записи: при входе с другого устройства он восстановится."""
    user.locale = body.locale
    db.commit()
    return user_out(db, user)
