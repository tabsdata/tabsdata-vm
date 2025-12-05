from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tdtui.core.models import Base, Instance, ApiResponse  # your ORM models
from tdtui.core.find_instances import sync_filesystem_instances_to_db, query_session


def start_session():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    Base.metadata.create_all(engine)
    sync_filesystem_instances_to_db(session=session)
    return session, Base


session = start_session()[0]
x = query_session(session=session, model=Instance, status="Not Running")
for inst in x:
    print({c.name: getattr(inst, c.name) for c in inst.__table__.columns})
