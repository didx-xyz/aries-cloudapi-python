import pytest
from httpx import AsyncClient

from shared import CLOUDAPI_URL


@pytest.mark.anyio
async def test_error_handler():
    async with AsyncClient(base_url=CLOUDAPI_URL) as client:
        response = await client.get("/generic/connections")
        assert response.status_code == 403
        assert response.text == '{"detail":"Not authenticated"}'
