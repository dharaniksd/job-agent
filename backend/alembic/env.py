"""
Alembic environment configuration.
Uses sync psycopg2 driver (Alembic doesn't support asyncpg directly).
"""
import os
import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure app package is importable
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override DB URL from environment (swap asyncpg → psycopg2 for Alembic)
db_url = os.getenv("DATABASE_URL", "").replace(
    "postgresql+asyncpg", "postgresql+psycopg2"
).replace("postgresql://", "postgresql+psycopg2://")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
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
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
