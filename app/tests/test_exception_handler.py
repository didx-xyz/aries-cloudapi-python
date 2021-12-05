import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_error_handler():
    async with AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get("/admin/wallet-multitenant/query-subwallet")
        assert response.status_code == 403
        assert response.text == '{"detail":"Not authenticated"}'
