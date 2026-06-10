"""
Dependencias de autorización basadas en rol.

La autorización lee el rol DESDE LA BASE DE DATOS en cada request (no desde el
token) para que un cambio de rol surta efecto de inmediato y no queden privilegios
obsoletos en tokens emitidos previamente.
"""
from typing import Annotated
from fastapi import Depends, HTTPException
from starlette import status
from sqlalchemy.orm import Session

from ..database.core import DbSession
from ..entities.user import User
from ..exceptions import AuthenticationError
from .service import CurrentUser
from . import roles


def get_user_role(db: Session, user_id) -> roles.UserRole:
    """Obtiene el rol de un usuario desde la BD (default redactor si no existe)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return roles.DEFAULT_ROLE
    return roles.normalize_role(user.role)


def is_admin_user(db: Session, user_id) -> bool:
    """True si el usuario tiene rol admin o master (según la BD)."""
    if user_id is None:
        return False
    return roles.is_admin(get_user_role(db, user_id))


def get_admin_user_ids(db: Session) -> set:
    """
    Conjunto de IDs (str) de usuarios con rol admin o master, leídos desde la BD.

    Reemplaza a la antigua lista hardcodeada settings.ADMIN_USER_IDS: la columna
    users.role es la única fuente de verdad.
    """
    rows = (
        db.query(User.id)
        .filter(User.role.in_([roles.UserRole.ADMIN.value, roles.UserRole.MASTER.value]))
        .all()
    )
    return {str(uid) for (uid,) in rows}


def get_current_user_entity(current_user: CurrentUser, db: DbSession) -> User:
    user = db.query(User).filter(User.id == current_user.get_uuid()).first()
    if not user:
        raise AuthenticationError()
    return user


def require_admin(current_user: CurrentUser, db: DbSession) -> User:
    user = get_current_user_entity(current_user, db)
    if not roles.is_admin(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de administrador.",
        )
    return user


def require_supervisor(current_user: CurrentUser, db: DbSession) -> User:
    """editor, admin o master."""
    user = get_current_user_entity(current_user, db)
    if not roles.is_supervisor(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol de administrador o editor.",
        )
    return user


def require_master(current_user: CurrentUser, db: DbSession) -> User:
    """Solo master: gestión de usuarios."""
    user = get_current_user_entity(current_user, db)
    if not roles.is_master(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere rol master.",
        )
    return user


AdminUser = Annotated[User, Depends(require_admin)]
SupervisorUser = Annotated[User, Depends(require_supervisor)]
MasterUser = Annotated[User, Depends(require_master)]
