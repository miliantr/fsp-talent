from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, NotFound, Unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import CandidateProfile, EmployerProfile, Role, User

bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB, cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if cred is None:
        raise Unauthorized("Требуется авторизация")
    try:
        payload = decode_access_token(cred.credentials)
    except jwt.PyJWTError as e:
        raise Unauthorized("Недействительный или просроченный токен") from e
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise Unauthorized("Пользователь не найден или заблокирован")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_candidate(db: DB, user: CurrentUser) -> CandidateProfile:
    if user.role != Role.CANDIDATE:
        raise Forbidden("Доступно только кандидатам")
    profile = db.query(CandidateProfile).filter_by(user_id=user.id).one_or_none()
    if not profile:
        raise NotFound("Профиль кандидата не найден")
    return profile


def require_employer(db: DB, user: CurrentUser) -> EmployerProfile:
    if user.role != Role.EMPLOYER:
        raise Forbidden("Доступно только работодателям")
    profile = db.query(EmployerProfile).filter_by(user_id=user.id).one_or_none()
    if not profile:
        raise NotFound("Профиль работодателя не найден")
    return profile


Candidate = Annotated[CandidateProfile, Depends(require_candidate)]
Employer = Annotated[EmployerProfile, Depends(require_employer)]
