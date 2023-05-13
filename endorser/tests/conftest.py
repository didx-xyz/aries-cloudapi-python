import pytest

from tests.fixtures import mock_agent_controller


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"
