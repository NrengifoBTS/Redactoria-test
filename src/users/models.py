from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional

from src.auth.roles import UserRole


class UserResponse(BaseModel):
    id: UUID
    # Opcional: el listado oculta el email a usuarios no-admin (ver users/controller).
    email: Optional[EmailStr] = None
    first_name: str
    last_name: str
    role: UserRole = UserRole.REDACTOR
    is_active: bool = True

    model_config = {"from_attributes": True}


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    new_password_confirm: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    role: UserRole = UserRole.REDACTOR


class UpdateUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class SetActiveRequest(BaseModel):
    is_active: bool
