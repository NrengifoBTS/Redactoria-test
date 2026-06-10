"""
Roles de usuario y predicados de permisos.

Fuente de verdad de los permisos por rol. La columna `role` en la tabla `users`
es la única fuente de verdad sobre qué rol tiene cada usuario; estas funciones
solo traducen un rol en capacidades concretas.

Jerarquía: master > admin > editor > redactor (default).
- master: todo lo de admin + ÚNICO que gestiona usuarios (crear/editar/eliminar/roles).
- admin: crea landing pages, ve analytics, edita contenido de otros.
- editor: crea blogs, edita contenido de otros.
- redactor: crea/edita su propio contenido.
"""
from enum import Enum


class UserRole(str, Enum):
    MASTER = "master"
    ADMIN = "admin"
    EDITOR = "editor"
    REDACTOR = "redactor"


DEFAULT_ROLE = UserRole.REDACTOR

# Nivel jerárquico (mayor = más privilegios).
_LEVEL = {
    UserRole.REDACTOR: 0,
    UserRole.EDITOR: 1,
    UserRole.ADMIN: 2,
    UserRole.MASTER: 3,
}


def normalize_role(role) -> UserRole:
    """Convierte un string/None en un UserRole, cayendo al default si es inválido."""
    if isinstance(role, UserRole):
        return role
    try:
        return UserRole(str(role))
    except (ValueError, TypeError):
        return DEFAULT_ROLE


def _level(role) -> int:
    return _LEVEL[normalize_role(role)]


def is_master(role) -> bool:
    return normalize_role(role) == UserRole.MASTER


def is_admin(role) -> bool:
    """admin o master (master hereda todas las capacidades de admin)."""
    return _level(role) >= _LEVEL[UserRole.ADMIN]


def is_supervisor(role) -> bool:
    """editor, admin o master: pueden ver y editar contenido de otros."""
    return _level(role) >= _LEVEL[UserRole.EDITOR]


# Capacidades nombradas (wrappers legibles sobre los predicados base)
def can_create_landing_page(role) -> bool:
    return is_admin(role)


def can_create_blog(role) -> bool:
    return is_supervisor(role)


def can_edit_others_content(role) -> bool:
    return is_supervisor(role)


def can_view_all_content(role) -> bool:
    return is_supervisor(role)


def can_delete_others_content(role) -> bool:
    return is_admin(role)


def can_view_analytics(role) -> bool:
    return is_admin(role)


def can_manage_users(role) -> bool:
    """Solo master puede gestionar usuarios (crear/editar/eliminar/asignar roles)."""
    return is_master(role)
