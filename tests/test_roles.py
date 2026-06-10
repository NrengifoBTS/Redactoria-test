from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.auth import roles
from src.auth.service import get_password_hash
from src.entities.user import User
from src.blog import service as blog_service
from src.blog import models as blog_models
from src.users import service as users_service
from src.users import models as users_models


def _make_user(db, role):
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        first_name="A",
        last_name="B",
        password_hash=get_password_hash("x"),
        role=role,
    )
    db.add(user)
    db.commit()
    return user


def _blog_payload():
    return blog_models.BlogCreate(
        title="Titulo",
        categoria="Autos",
        keywords="alquiler, autos",
        idioma="es",
        tecnica="seo",
        acento="neutro",
    )


def test_role_predicates():
    assert roles.is_admin("admin")
    assert not roles.is_admin("editor")

    assert roles.is_supervisor("admin")
    assert roles.is_supervisor("editor")
    assert not roles.is_supervisor("redactor")

    assert roles.can_create_landing_page("admin")
    assert not roles.can_create_landing_page("editor")

    assert roles.can_create_blog("editor")
    assert not roles.can_create_blog("redactor")

    # master: superset de admin + único que gestiona usuarios
    assert roles.is_master("master")
    assert not roles.is_master("admin")
    assert roles.is_admin("master")  # hereda admin
    assert roles.is_supervisor("master")
    assert roles.can_manage_users("master")
    assert not roles.can_manage_users("admin")

    # valores inválidos / None caen al rol por defecto (redactor)
    assert not roles.is_admin(None)
    assert roles.normalize_role("cualquier-cosa") == roles.UserRole.REDACTOR


def test_register_default_role_is_redactor(db_session):
    user = _make_user(db_session, roles.DEFAULT_ROLE.value)
    assert user.role == "redactor"


def test_update_user_role(db_session):
    user = _make_user(db_session, "redactor")
    users_service.update_user(
        db_session, user.id, users_models.UpdateUserRequest(role=roles.UserRole.EDITOR)
    )
    refreshed = users_service.get_user_by_id(db_session, user.id)
    assert refreshed.role == "editor"


def test_create_and_update_user(db_session):
    created = users_service.create_user(
        db_session,
        users_models.CreateUserRequest(
            email="nuevo@example.com",
            first_name="Nuevo",
            last_name="Usuario",
            password="secret123",
            role=roles.UserRole.ADMIN,
        ),
    )
    assert created.role == "admin"
    updated = users_service.update_user(
        db_session,
        created.id,
        users_models.UpdateUserRequest(first_name="Editado"),
    )
    assert updated.first_name == "Editado"
    assert updated.role == "admin"


def test_redactor_cannot_create_blog(db_session):
    user = _make_user(db_session, "redactor")
    current = blog_service.CurrentUser(user.id)
    with pytest.raises(HTTPException) as exc:
        blog_service.create_blog(current, db_session, _blog_payload())
    assert exc.value.status_code == 403


def test_editor_can_create_blog(db_session):
    user = _make_user(db_session, "editor")
    current = blog_service.CurrentUser(user.id)
    blog = blog_service.create_blog(current, db_session, _blog_payload())
    assert blog.created_by == user.id


def test_admin_can_create_blog(db_session):
    user = _make_user(db_session, "admin")
    current = blog_service.CurrentUser(user.id)
    blog = blog_service.create_blog(current, db_session, _blog_payload())
    assert blog.created_by == user.id
