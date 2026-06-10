"""add users.role + seed de roles iniciales

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Semilla de admins: unión del backend + el extra que existía solo en el frontend,
# para que nadie pierda el rol al migrar.
ADMIN_SEED = [
    "65cd97a4-c3b9-4bfd-b014-55457ae847e3",
    "f49cda9b-2138-435e-a497-fda85be87e63",
    "c7c17838-074d-44fa-9248-8dc87c15edd5",
    "152c46be-e2f4-48da-86b1-592af570624a",
    "b43f1d04-f339-4cf9-8e4e-4f127f12af5a",
    "2fd1e540-40be-42cf-9d2b-693b0d3132af",
    "4007b1aa-30a9-4167-8535-639180f8fbc4",
]

# Editores (del frontend roles.js), excluyendo a quienes ya son admin.
EDITOR_SEED = [
    "a1116359-0fd7-43b4-b4eb-231bc2a14a21",
    "4e7a5222-8bd5-45c5-bdcd-e4dc1dbfe27d",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}

    # Idempotente: solo agrega la columna si aún no existe.
    if "role" not in columns:
        op.add_column(
            "users",
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=False,
                server_default="redactor",
            ),
        )

    # Sembrar roles a partir de las listas previas.
    op.execute(
        sa.text("UPDATE users SET role = 'admin' WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True, value=ADMIN_SEED)
        )
    )
    op.execute(
        sa.text(
            "UPDATE users SET role = 'editor' WHERE id IN :ids AND role <> 'admin'"
        ).bindparams(sa.bindparam("ids", expanding=True, value=EDITOR_SEED))
    )


def downgrade() -> None:
    op.drop_column("users", "role")
