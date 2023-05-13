import pytest

from tests.fixtures import mock_agent_controller


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"
