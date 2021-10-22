from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trustregistry import database
from trustregistry import main

Base = database.Base
app = main.app
get_db = main.get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_root():
    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.json() == {"actors": [], "schemas": []}


def test_registry():
    resp = client.get("/registry")

    assert resp.status_code == 200
    assert resp.json() == {"actors": [], "schemas": []}
