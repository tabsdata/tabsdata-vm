import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tdconsole.core.find_instances import sync_filesystem_instances_to_db
from tdconsole.core.models import Base  # your ORM models

def _default_db_url() -> str:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return f"sqlite:///{(base / 'tdconsole' / 'tdconsole.db').resolve()}"


def _sqlite_db_path(db_url: str) -> Path | None:
    if not db_url.startswith("sqlite:///"):
        return None
    path = db_url.replace("sqlite:///", "", 1)
    path = path.split("?", 1)[0]
    return Path(path).expanduser()


def _resolve_db_url(db_url: str | None) -> str:
    if db_url is not None:
        return db_url
    env_url = os.environ.get("TDCONSOLE_DB_URL")
    if env_url:
        return env_url

    default_url = _default_db_url()
    db_path = _sqlite_db_path(default_url)
    if db_path is None:
        return default_url

    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(db_path.parent, os.W_OK):
            raise PermissionError
    except PermissionError:
        fallback_path = Path("/tmp/tdconsole/tdconsole.db")
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{fallback_path}"

    return default_url


def _ensure_sqlite_dir(db_url: str) -> None:
    """Create parent directory for SQLite files if needed."""
    db_path = _sqlite_db_path(db_url)
    if db_path is None:
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(db_path.parent, os.W_OK):
        raise PermissionError(f"Directory not writable: {db_path.parent}")


def start_session(db_url: str | None = None):
    url = _resolve_db_url(db_url)
    try:
        _ensure_sqlite_dir(url)
    except PermissionError as exc:
        raise RuntimeError(
            "SQLite database path is not writable. "
            "Set TDCONSOLE_DB_URL to a writable location, e.g. "
            "'sqlite:////tmp/tdconsole/tdconsole.db'."
        ) from exc
    engine = create_engine(url, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    Base.metadata.create_all(engine)
    sync_filesystem_instances_to_db(session=session)
    # Base.metadata.drop_all(engine)
    # Base.metadata.create_all(engine)
    return session, Base


# session = start_session()[0]
# x = query_session(session=session, model=Instance, status="Not Running")
# for inst in x:
#     print({c.name: getattr(inst, c.name) for c in inst.__table__.columns})
