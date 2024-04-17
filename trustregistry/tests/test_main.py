import pytest
from trustregistry.main import app, lifespan, root, registry
from unittest.mock import MagicMock, patch, Mock
from fastapi import FastAPI
from sqlalchemy.orm import Session
from trustregistry import db



@pytest.fixture
def db_session_mock():
    session = Mock(spec=Session)
    return session


def test_create_app():
    assert app.title == "Trust Registry"

    # Verifying that all routes are included

    # Get all routes in app
    routes = [route.path for route in app.routes]

    expected_routes = ["/", "/registry"]
    for route in expected_routes:
        assert route in routes


@patch('trustregistry.main.inspect')
@patch('trustregistry.main.engine')
@pytest.mark.anyio
async def test_lifespan(mock_engine, mock_inspect):
    mock_inspector = MagicMock()
    mock_inspect.return_value = mock_inspector
    mock_inspector.get_table_names.return_value = ['table1', 'table2']
    mock_connection = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection

    async with lifespan(FastAPI()):
        pass

    mock_engine.dispose.assert_called_once()
    mock_engine.connect.assert_called_once()
    mock_inspect.assert_called_once_with(mock_connection)
    mock_inspector.get_table_names.assert_called_once()

@pytest.mark.anyio
async def test_root():
    schemas = [
                db.Schema(id="123", did="did:123", name="schema1", version="1.0"),
                db.Schema(id="456", did="did:123", name="schema2", version="1.0"),
            ]
    actors = [db.Actor(id="1", name="Alice"), db.Actor(id="2", name="Bob")]
    with patch('trustregistry.main.crud.get_schemas') as mock_get_schemas, \
            patch('trustregistry.main.crud.get_actors') as mock_get_actors:
        mock_get_schemas.return_value = schemas
        mock_get_actors.return_value = actors

        response = await root(db_session_mock)

        assert response == {"actors": actors, "schemas": ['123', '456']}

        mock_get_schemas.assert_called_once_with(db_session_mock)
        mock_get_actors.assert_called_once_with(db_session_mock)


@pytest.mark.anyio
async def test_registry():
    with patch('trustregistry.main.root') as mock_root:
        mock_root.return_value = {'actors': 'actors', 'schemas': 'schemas'}

        response = await registry(db_session_mock)

        assert response == {'actors': 'actors', 'schemas': 'schemas'}

        mock_root.assert_called_once_with(db_session_mock)
