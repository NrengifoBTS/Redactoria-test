"""asignar rol master a tamara (único master del sistema)

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MASTER_EMAIL = "tamarar@redactoria.com"


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET role = 'master' WHERE email = :email").bindparams(
            email=MASTER_EMAIL
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE users SET role = 'admin' WHERE email = :email").bindparams(
            email=MASTER_EMAIL
        )
    )
