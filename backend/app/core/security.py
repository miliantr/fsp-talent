"""Password hashing and access tokens.

Tokens are OIDC-shaped JWTs (sub, email, iss, realm_access.roles) — the same claims Keycloak
issues — so switching to FSP ID / Keycloak means swapping the verifier (HS256 secret -> JWKS RS256)
in `decode_access_token`, not touching the endpoints.
"""

import hashlib
import secrets
from datetime import timedelta

import bcrypt
import jwt

from app.core.config import get_settings
from app.db.base import utcnow


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, email: str, role: str) -> str:
    s = get_settings()
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "email": email,
        "iss": s.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=s.access_token_ttl_minutes)).timestamp()),
        "realm_access": {"roles": [role]},
        "typ": "Bearer",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    s = get_settings()
    return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm], issuer=s.jwt_issuer,
                      options={"verify_iat": False})


def new_email_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()
