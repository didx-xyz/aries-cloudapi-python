from sqlalchemy import Column, String

from trustregistry.database import Base


def schema_id_gen(context):
    did = context.get_current_parameters()["did"]
    name = context.get_current_parameters()["name"]
    version = context.get_current_parameters()["version"]
    return f"{did}:{name}:{version}"


class Actor(Base):
    __tablename__ = "actors"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    roles = Column(String, index=True)
    didcomm_invitation = Column(String, unique=True, index=True)
    did = Column(String, unique=True, index=True)


class Schema(Base):
    __tablename__ = "schemas"

    id = Column(
        String,
        primary_key=True,
        index=True,
        default=schema_id_gen,
        onupdate=schema_id_gen,
    )
    did = Column(String, index=True)
    name = Column(String, index=True)
    version = Column(String, index=True)
