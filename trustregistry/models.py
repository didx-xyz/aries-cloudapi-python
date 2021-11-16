from sqlalchemy import Column, String

from trustregistry.list_type import StringList
from trustregistry.database import Base


def schema_id_gen(context):
    parameters = context.get_current_parameters()
    did = parameters["did"]
    name = parameters["name"]
    version = parameters["version"]
    return f"{did}:2:{name}:{version}"


class Actor(Base):
    __tablename__ = "actors"

    id = Column(String, primary_key=True, index=True, unique=True)
    name = Column(String, unique=True, index=True)
    roles = Column(StringList, index=True)
    didcomm_invitation = Column(String, unique=True, index=True)
    did = Column(String, unique=True, index=True)


class Schema(Base):
    __tablename__ = "schemas"

    id = Column(
        String,
        primary_key=True,
        index=True,
        unique=True,
        default=schema_id_gen,
        onupdate=schema_id_gen,
    )
    did = Column(String, index=True)
    name = Column(String, index=True)
    version = Column(String, index=True)
