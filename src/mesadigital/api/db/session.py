from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from mesadigital.api import settings

_connect_args: dict[str, object] = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a session and closes it on exit.

    Use as ``Depends(get_db)`` in route signatures, or wrap with
    ``contextlib.contextmanager`` / ``asynccontextmanager`` for manual usage.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
