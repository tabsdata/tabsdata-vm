from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import declarative_base, relationship

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

    collections = relationship(
        "Collection",
        back_populates="instance",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def ext_socket(self):
        return f"{self.public_ip}:{self.arg_ext}"

    @ext_socket.expression
    def ext_socket(cls):
        return cls.public_ip + ":" + cls.arg_ext.cast(String)

    @hybrid_property
    def int_socket(self):
        return f"{self.private_ip}:{self.arg_int}"

    @int_socket.expression
    def int_socket(cls):
        return cls.private_ip + ":" + cls.arg_int.cast(String)


class Collection(Base):
    __tablename__ = "collections"

    name = Column(String, nullable=True, primary_key=True)

    instance_name = Column(
        String, ForeignKey("instances.name"), nullable=False, primary_key=True
    )
    instance = relationship("Instance", back_populates="collections")

    functions = relationship(
        "Function",
        back_populates="collection",
        cascade="all, delete-orphan",
    )
    tables = relationship(
        "Table",
        back_populates="collection",
        cascade="all, delete-orphan",
    )


class Function(Base):
    __tablename__ = "functions"

    collection_name = Column(
        String, ForeignKey("collections.name"), nullable=False, primary_key=True
    )
    collection = relationship("Collection", back_populates="functions")
    instance_name = Column(String, primary_key=True)

    name = Column(String, nullable=True, primary_key=True)


class Table(Base):
    __tablename__ = "tables"

    collection_name = Column(
        String, ForeignKey("collections.name"), nullable=False, primary_key=True
    )
    collection = relationship("Collection", back_populates="tables")
    instance_name = Column(String, primary_key=True)

    name = Column(String, nullable=True, primary_key=True)


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
