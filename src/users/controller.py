from fastapi import APIRouter, status
from uuid import UUID
from typing import List

from ..database.core import DbSession
from . import models
from . import service
from ..auth.service import CurrentUser
from ..auth.permissions import MasterUser, is_admin_user

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me", response_model=models.UserResponse)
def get_current_user(current_user: CurrentUser, db: DbSession):
    return service.get_user_by_id(db, current_user.get_uuid())

@router.get("/", response_model=List[models.UserResponse])
def get_users(db: DbSession, current_user: CurrentUser):
    """
    Listado de usuarios. Cualquier autenticado lo necesita para resolver
    "asignado a" en los dashboards, pero el email solo se expone a admin/master;
    el resto recibe id, nombre y rol.
    """
    users = service.get_all_users(db)
    result = [models.UserResponse.model_validate(u) for u in users]
    if not is_admin_user(db, current_user.get_uuid()):
        for r in result:
            r.email = None
    return result

@router.put("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    password_change: models.PasswordChange,
    db: DbSession,
    current_user: CurrentUser
):
    service.change_password(db, current_user.get_uuid(), password_change)


# =======================================================================
# Gestión de usuarios — SOLO MASTER
# =======================================================================

@router.post("/", response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: models.CreateUserRequest, db: DbSession, master: MasterUser):
    """Crear un usuario nuevo. Solo master."""
    return service.create_user(db, payload)


@router.put("/{user_id}", response_model=models.UserResponse)
def update_user(user_id: UUID, payload: models.UpdateUserRequest, db: DbSession, master: MasterUser):
    """Editar datos y/o rol de un usuario. Solo master."""
    return service.update_user(db, user_id, payload)


@router.put("/{user_id}/password", status_code=status.HTTP_200_OK)
def reset_user_password(
    user_id: UUID, payload: models.ResetPasswordRequest, db: DbSession, master: MasterUser
):
    """Resetear la contraseña de un usuario. Solo master."""
    service.reset_user_password(db, user_id, payload.new_password)


@router.put("/{user_id}/active", response_model=models.UserResponse)
def set_user_active(
    user_id: UUID, payload: models.SetActiveRequest, db: DbSession, master: MasterUser
):
    """Activar o desactivar una cuenta (soft-delete). Solo master. Los usuarios no se eliminan."""
    return service.set_user_active(db, user_id, payload.is_active, master.id)
