from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()


class Instance(Base):
    __tablename__ = "instances"

    name = Column(String, unique=True, nullable=False, primary_key=True)

    pid = Column(String, nullable=True, default=None)
    working = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="Not Running")
    cfg_ext = Column(String, nullable=True, default="2457")
    cfg_int = Column(String, nullable=True, default="2458")
    arg_ext = Column(String, nullable=True, default="2457")
    arg_int = Column(String, nullable=True, default="2458")
    private_ip = Column(String, nullable=True, default="127.0.0.1")
    public_ip = Column(String, nullable=True, default="127.0.0.1")
    use_https = Column(Boolean, nullable=True, default=False)

    @hybrid_property
    def ext_socket(self):
        return f"{self.public_ip}:{self.arg_ext}"

    @ext_socket.expression
    def socket(cls):
        return cls.public_ip + ":" + cls.arg_ext.cast(String)

    @hybrid_property
    def int_socket(self):
        return f"{self.private_ip}:{self.arg_int}"

    @int_socket.expression
    def socket(cls):
        return cls.private_ip + ":" + cls.arg_int.cast(String)


class ApiResponse(Base):
    __tablename__ = "api_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    screen = Column(String, unique=False, nullable=True)
    label = Column(String, unique=False, nullable=True)
    priority = Column(Integer, unique=False, nullable=True)


def get_model_by_tablename(tablename: str):
    for mapper in Base.registry.mappers:
        if mapper.local_table.name == tablename:
            return mapper.class_
    raise LookupError(f"No model found for table {tablename!r}")
