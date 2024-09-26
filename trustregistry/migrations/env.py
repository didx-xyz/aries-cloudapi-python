import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from shared.log_config import get_logger
from trustregistry.db import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Get db url from environment variable
db_url = os.environ.get("POSTGRES_DATABASE_URL", "test123")
print(f"db_url: {db_url}")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = get_logger(__name__)


# Get the database URL from environment variable
db_url = os.environ.get("POSTGRES_DATABASE_URL")

if db_url:
    logger.info(f"Using database URL from environment: {db_url}")
    config.set_main_option("sqlalchemy.url", db_url)
else:
    logger.warning(
        "POSTGRES_DATABASE_URL not set in environment. Using default URL from alembic.ini"
    )
    db_url = config.get_main_option("sqlalchemy.url")

# Verify that we have a valid database URL
if not db_url:
    raise ValueError(
        "Database URL is not set. Please set POSTGRES_DATABASE_URL environment variable or provide a valid sqlalchemy.url in alembic.ini"
    )

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
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
