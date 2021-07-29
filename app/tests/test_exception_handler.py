import pytest


@pytest.mark.asyncio
async def test_error_handler(async_client):
    response = await async_client.get("/admin/wallet-multitenant/query-subwallet")
    assert response.status_code == 401
