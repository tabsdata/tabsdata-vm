from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    pid = Column(String, nullable=True)
    status = Column(String, nullable=False)
    cfg_ext = Column(String, nullable=True)
    cfg_int = Column(String, nullable=True)
    arg_ext = Column(String, nullable=True)
    arg_int = Column(String, nullable=True)
