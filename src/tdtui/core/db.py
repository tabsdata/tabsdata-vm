from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tdtui.core.models import Base, Instance  # your ORM models


def start_session():
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    return SessionLocal()


# x = start_session()


# with x as session:
#     inst = session.query(Instance).filter_by(name="td-1").first()

#     if not inst:
#         inst = Instance(name="td-1", status="running")
#         session.add(inst)
#     inst = session.query(Instance).filter_by(name="td-1").first()
#     session.commit()
