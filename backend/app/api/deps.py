from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import Forbidden, NotFound, Unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.i18n import t
from app.models import CandidateProfile, EmployerProfile, Role, User

bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def get_current_user(db: DB, cred: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if cred is None:
        raise Unauthorized(t("error.auth_required"))
    try:
        payload = decode_access_token(cred.credentials)
    except jwt.PyJWTError as e:
        raise Unauthorized(t("error.token_invalid")) from e
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise Unauthorized(t("error.user_inactive"))
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_candidate(db: DB, user: CurrentUser) -> CandidateProfile:
    if user.role != Role.CANDIDATE:
        raise Forbidden(t("error.candidates_only"))
    profile = db.query(CandidateProfile).filter_by(user_id=user.id).one_or_none()
    if not profile:
        raise NotFound(t("error.candidate_profile_missing"))
    return profile


def require_employer(db: DB, user: CurrentUser) -> EmployerProfile:
    if user.role != Role.EMPLOYER:
        raise Forbidden(t("error.employers_only"))
    profile = db.query(EmployerProfile).filter_by(user_id=user.id).one_or_none()
    if not profile:
        raise NotFound(t("error.employer_profile_missing"))
    return profile


Candidate = Annotated[CandidateProfile, Depends(require_candidate)]
Employer = Annotated[EmployerProfile, Depends(require_employer)]
