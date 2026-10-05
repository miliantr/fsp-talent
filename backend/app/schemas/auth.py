from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["candidate", "employer"]
    consent_processing: bool = Field(description="Согласие на обработку персональных данных (152-ФЗ)")
    first_name: str = Field(default="", max_length=64)
    last_name: str = Field(default="", max_length=64)
    company_name: str = Field(default="", max_length=128)


class RegisterOut(BaseModel):
    email: str
    verification_required: bool = True
    dev_code: str | None = Field(default=None, description="Только в демо-режиме: код подтверждения")


class VerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendIn(BaseModel):
    email: EmailStr


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    is_email_verified: bool
    display_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
