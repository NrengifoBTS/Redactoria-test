import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# --- Metadata objetivo -------------------------------------------------------
# Importamos Base y los módulos de entidades para que todos los mappers queden
# registrados en Base.metadata (necesario para autogenerate). Importamos SOLO
# entidades, no la app completa, para no arrastrar routers/dependencias pesadas.
from src.database.core import Base
from src.entities import (  # noqa: F401
    user,
    todo,
    proyecto,
    template,
    landing_page,
    seccion_lp,
    anotacion,
    blog,
    scraping,
    ria_v2,
)
from src.entities.logging import (  # noqa: F401
    ai_generation,
    user_edit,
    user_style_profile,
    training_dataset,
    narrative_flow,
    translation_quality,
)

config = context.config

# La URL real viene de la variable de entorno DATABASE_URL.
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
