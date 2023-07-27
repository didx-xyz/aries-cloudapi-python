import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

POSTGRES_DATABASE_URL = os.getenv(
    "POSTGRES_DATABASE_URL",
    "postgresql://trustregistry:trustregistry@trustregistry-db:5432/trustregistry",
)
engine = create_engine(POSTGRES_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
