import mockito
import pytest

# pylint: disable=unused-import
from tests.fixtures import mock_agent_controller  # noqa: F401


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def unstub_mockito():
    """
    Automatically unstub all stubbed methods after each test.
    """
    # Setup phase: No setup needed in this fixture

    yield

    # Teardown phase: After each test, unstub all stubbed methods
    mockito.unstub()
