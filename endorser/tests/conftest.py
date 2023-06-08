import mockito
import pytest

# pylint: disable=unused-import
from shared.util.mock_agent_controller import mock_agent_controller  # noqa: F401


@pytest.fixture(scope="session")
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
