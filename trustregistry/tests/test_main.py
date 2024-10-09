from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from trustregistry import db
from trustregistry.main import app, check_migrations, lifespan, registry, root


@pytest.fixture
def db_session_mock():
    session = Mock(spec=Session)
    return session


def test_create_app():
    assert app.title == "Trust Registry"

    routes = [route.path for route in app.routes]

    expected_routes = ["/", "/registry", "/docs"]
    for route in expected_routes:
        assert route in routes


@pytest.mark.anyio
@patch("trustregistry.main.check_migrations")
@patch("trustregistry.main.Config")
@patch("trustregistry.main.command")
@patch("trustregistry.main.logger")
async def test_lifespan_migrations_needed(
    mock_logger, mock_command, mock_config, mock_check_migrations
):
    mock_check_migrations.return_value = False
    mock_config.return_value = MagicMock()

    async with lifespan(FastAPI()):
        pass

    mock_command.upgrade.assert_called_once_with(mock_config.return_value, "head")
    mock_logger.info.assert_any_call("Applying database migrations...")
    mock_logger.info.assert_any_call("Database schema is up to date.")


@pytest.mark.anyio
@patch("trustregistry.main.check_migrations")
@patch("trustregistry.main.Config")
@patch("trustregistry.main.command")
@patch("trustregistry.main.logger")
async def test_lifespan_already_exists_error(
    mock_logger, mock_command, mock_config, mock_check_migrations
):
    mock_check_migrations.return_value = False
    mock_config.return_value = MagicMock()
    mock_command.upgrade.side_effect = ProgrammingError(
        "Table already exists", None, None
    )

    async with lifespan(FastAPI()):
        pass

    mock_command.stamp.assert_called_once_with(mock_config.return_value, "head")
    mock_logger.warning.assert_called_once_with(
        "Database schema already exists. Stamping with current version."
    )
    mock_logger.info.assert_called_with(
        "Database stamped with current migration version."
    )


@pytest.mark.anyio
@patch("trustregistry.main.check_migrations")
@patch("trustregistry.main.Config")
@patch("trustregistry.main.command")
@patch("trustregistry.main.logger")
async def test_lifespan_unexpected_error(
    mock_logger, mock_command, mock_config, mock_check_migrations
):
    mock_check_migrations.return_value = False
    mock_config.return_value = MagicMock()
    mock_command.upgrade.side_effect = ProgrammingError("Unexpected error", None, None)

    with pytest.raises(ProgrammingError):
        async with lifespan(FastAPI()):
            pass

    mock_logger.error.assert_called_once()


@pytest.mark.anyio
@patch("trustregistry.main.check_migrations")
@patch("trustregistry.main.logger")
async def test_lifespan_no_migrations_needed(mock_logger, mock_check_migrations):
    mock_check_migrations.return_value = True

    async with lifespan(FastAPI()):
        pass

    mock_logger.info.assert_called_once_with(
        "Database is up to date. No migrations needed."
    )


@pytest.mark.parametrize(
    "table_names,current_rev,head_rev,expected",
    [
        ([], None, None, False),  # alembic_version table doesn't exist
        (
            ["alembic_version"],
            "current_rev",
            "head_rev",
            False,
        ),  # revisions don't match
        (["alembic_version"], "same_rev", "same_rev", True),  # revisions match
    ],
)
@patch("trustregistry.main.inspect")
@patch("trustregistry.main.MigrationContext")
@patch("trustregistry.main.Config")
@patch("trustregistry.main.ScriptDirectory")
def test_check_migrations(
    mock_script_directory,
    mock_config,
    mock_migration_context,
    mock_inspect,
    table_names,
    current_rev,
    head_rev,
    expected,
):
    # Set up mocks
    mock_inspector = MagicMock()
    mock_inspector.get_table_names.return_value = table_names
    mock_inspect.return_value = mock_inspector

    mock_context = MagicMock()
    mock_context.get_current_revision.return_value = current_rev
    mock_migration_context.configure.return_value = mock_context

    mock_script = MagicMock()
    mock_script.get_current_head.return_value = head_rev
    mock_script_directory.from_config.return_value = mock_script

    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_connection

    # Run the function
    result = check_migrations(mock_engine)

    # Assert the result
    assert result == expected

    # Verify mock calls
    mock_inspect.assert_called_with(mock_connection)
    mock_inspector.get_table_names.assert_called_once()
    if table_names:  # Only check these if alembic_version table exists
        mock_migration_context.configure.assert_called_with(mock_connection)
        mock_context.get_current_revision.assert_called_once()
        mock_config.assert_called_with("alembic.ini")
        mock_script_directory.from_config.assert_called_once()
        mock_script.get_current_head.assert_called_once()


@pytest.mark.anyio
async def test_root(db_session_mock):  # pylint: disable=redefined-outer-name
    schemas = [
        db.Schema(id="123", did="did:123", name="schema1", version="1.0"),
        db.Schema(id="456", did="did:123", name="schema2", version="1.0"),
    ]
    actors = [db.Actor(id="1", name="Alice"), db.Actor(id="2", name="Bob")]
    with patch("trustregistry.main.crud.get_schemas") as mock_get_schemas, patch(
        "trustregistry.main.crud.get_actors"
    ) as mock_get_actors:
        mock_get_schemas.return_value = schemas
        mock_get_actors.return_value = actors

        response = await root(db_session_mock)

        assert response == {"actors": actors, "schemas": ["123", "456"]}

        mock_get_schemas.assert_called_once_with(db_session_mock)
        mock_get_actors.assert_called_once_with(db_session_mock)


@pytest.mark.anyio
async def test_registry(db_session_mock):  # pylint: disable=redefined-outer-name
    with patch("trustregistry.main.root") as mock_root:
        mock_root.return_value = {"actors": "actors", "schemas": "schemas"}

        response = await registry(db_session_mock)

        assert response == {"actors": "actors", "schemas": "schemas"}

        mock_root.assert_called_once_with(db_session_mock)
