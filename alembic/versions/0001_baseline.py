"""baseline (esquema pre-existente, creado fuera de Alembic)

Revision ID: 0001
Revises:
Create Date: 2026-05-28

Esta revisión es intencionalmente vacía: las tablas ya existían antes de adoptar
Alembic. Sirve como punto de partida del historial. Una BD nueva y vacía NO se
construye con Alembic todavía (las tablas se crean fuera). A partir de aquí, todo
cambio de esquema se versiona como una nueva revisión.
"""
from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
