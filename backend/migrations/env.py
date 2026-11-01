import os
from alembic import context
from sqlalchemy import create_engine, pool
from app.db import Base
from app import models
from app.config import settings

url = os.environ.get("ADMIN_DATABASE_URL") or settings().database_url
url = url.replace("postgres://", "postgresql+psycopg://", 1) if url.startswith("postgres://") else url.replace("postgresql://", "postgresql+psycopg://", 1)
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url, poolclass=pool.NullPool, connect_args={"prepare_threshold": None}).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
