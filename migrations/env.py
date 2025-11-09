from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401 to register models


# Alembic Config object
config = context.config
settings = get_settings()

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use app metadata for autogenerate
target_metadata = Base.metadata

# --- Custom database URL setup ---
# Alembic must use a *sync* engine (async not supported)
sync_url = settings.database_url.replace("+asyncpg", "")

config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(sync_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        # include_schemas=True so Alembic compares objects across non-public schemas
        context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()