import pytest
from httpx import AsyncClient

from app.generic.connections.connections import router
from shared import CLOUDAPI_URL

CONNECTIONS_BASE_PATH = router.prefix


@pytest.mark.anyio
async def test_error_handler():
    async with AsyncClient(base_url=CLOUDAPI_URL) as client:
        response = await client.get(CONNECTIONS_BASE_PATH)
        assert response.status_code == 403
        assert response.text == '{"detail":"Not authenticated"}'
