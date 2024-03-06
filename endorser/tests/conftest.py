from unittest.mock import AsyncMock, MagicMock

import pytest
from aries_cloudcontroller import AcaPyClient, EndorseTransactionApi


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_acapy_client():
    client = MagicMock(spec=AcaPyClient)
    client.endorse_transaction = MagicMock(spec=EndorseTransactionApi)
    client.endorse_transaction.get_transaction = AsyncMock()
    client.endorse_transaction.endorse_transaction = AsyncMock()
    return client
