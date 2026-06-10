from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from . import models
from typing import List
from src.entities.user import User
from src.exceptions import UserNotFoundError, InvalidPasswordError, PasswordMismatchError
from src.auth.service import verify_password, get_password_hash
from src.auth.roles import is_master
import logging


def get_user_by_id(db: Session, user_id: UUID) -> models.UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logging.warning(f"User not found with ID: {user_id}")
        raise UserNotFoundError(user_id)
    logging.info(f"Successfully retrieved user with ID: {user_id}")
    return user

def get_all_users(db: Session) -> List[User]:
    """Obtener todos los usuarios del sistema"""
    try:
        users = db.query(User).all()
        logging.info(f"Retrieved {len(users)} users from database")
        return users
    except Exception as e:
        logging.error(f"Error retrieving users: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving users")


def create_user(db: Session, payload: models.CreateUserRequest) -> User:
    """Crear un usuario nuevo. Pensado para uso del master."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese email.",
        )
    user = User(
        id=uuid4(),
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password_hash=get_password_hash(payload.password),
        role=payload.role.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logging.info(f"User {user.id} created with role '{payload.role.value}'")
    return user


def update_user(db: Session, user_id: UUID, payload: models.UpdateUserRequest) -> User:
    """Editar datos y/o rol de un usuario. Pensado para uso del master."""
    user = get_user_by_id(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    new_email = data.get("email")
    if new_email and new_email != user.email:
        clash = db.query(User).filter(User.email == new_email).first()
        if clash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un usuario con ese email.",
            )
        user.email = new_email

    if "first_name" in data and data["first_name"] is not None:
        user.first_name = data["first_name"]
    if "last_name" in data and data["last_name"] is not None:
        user.last_name = data["last_name"]
    if data.get("role") is not None:
        user.role = data["role"].value

    db.commit()
    db.refresh(user)
    logging.info(f"User {user_id} updated (role now '{user.role}')")
    return user


def reset_user_password(db: Session, user_id: UUID, new_password: str) -> None:
    """Fijar una contraseña nueva para un usuario (master). Sin pedir la actual."""
    user = get_user_by_id(db, user_id)
    user.password_hash = get_password_hash(new_password)
    db.commit()
    logging.info(f"Password reset for user {user_id}")


def set_user_active(db: Session, user_id: UUID, is_active: bool, acting_user_id: UUID) -> User:
    """
    Activar / desactivar una cuenta (soft-delete). Los usuarios no se eliminan.
    Un usuario desactivado no puede iniciar sesión, pero conserva su contenido.
    Protecciones al desactivar: no al master, no a uno mismo.
    """
    user = get_user_by_id(db, user_id)

    if not is_active:
        if is_master(user.role):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede desactivar al master.",
            )
        if user.id == acting_user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puedes desactivar tu propia cuenta.",
            )

    user.is_active = is_active
    db.commit()
    db.refresh(user)
    logging.info(f"User {user_id} is_active set to {is_active} by {acting_user_id}")
    return user


def change_password(db: Session, user_id: UUID, password_change: models.PasswordChange) -> None:
    try:
        user = get_user_by_id(db, user_id)
        
        # Verify current password
        if not verify_password(password_change.current_password, user.password_hash):
            logging.warning(f"Invalid current password provided for user ID: {user_id}")
            raise InvalidPasswordError()
        
        # Verify new passwords match
        if password_change.new_password != password_change.new_password_confirm:
            logging.warning(f"Password mismatch during change attempt for user ID: {user_id}")
            raise PasswordMismatchError()
        
        # Update password
        user.password_hash = get_password_hash(password_change.new_password)
        db.commit()
        logging.info(f"Successfully changed password for user ID: {user_id}")
    except Exception as e:
        logging.error(f"Error during password change for user ID: {user_id}. Error: {str(e)}")
        raise
