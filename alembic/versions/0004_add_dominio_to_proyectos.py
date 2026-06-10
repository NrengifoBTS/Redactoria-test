"""add dominio destino a proyectos

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Columnas de dominio destino para la landing page del proyecto.
_NEW_COLUMNS = [
    ("dominio", sa.String(length=150)),
    ("dominio_url", sa.String(length=255)),
    ("dominio_pais", sa.String(length=120)),
    ("dominio_idiomas", sa.String(length=50)),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("proyectos")}

    # Idempotente: solo agrega las columnas que falten.
    for name, col_type in _NEW_COLUMNS:
        if name not in existing:
            op.add_column("proyectos", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_NEW_COLUMNS):
        op.drop_column("proyectos", name)
