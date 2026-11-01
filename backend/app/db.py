from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

MAINTENANCE_LOCK = 2026102701


class Base(DeclarativeBase):
    pass


url = settings().database_url
if url.startswith("postgres://"):
    url = "postgresql+psycopg://" + url[len("postgres://"):]
elif url.startswith("postgresql://"):
    url = "postgresql+psycopg://" + url[len("postgresql://"):]
engine = create_engine(url, pool_size=4, max_overflow=2, pool_pre_ping=True, pool_recycle=300, connect_args={"prepare_threshold": None})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        try:
            db.execute(text("SELECT pg_advisory_xact_lock_shared(:key)"), {"key": MAINTENANCE_LOCK})
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
