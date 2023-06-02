import pytest

from tests.fixtures import mock_agent_controller  # noqa: F401


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"
