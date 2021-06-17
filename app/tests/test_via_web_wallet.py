import pytest
from httpx import AsyncClient

from main import app


@pytest.mark.asyncio
async def test_root(setup_env):
    async with AsyncClient(app=app, base_url="http://localhost:8000") as ac:
        response = await ac.get("/wallets/create-pub-did", headers={"req-header": "{'api_key': 'adminApiKey'}"})
    assert response.status_code == 200
    result = response.json()

    assert result['did_object']['posture'] == 'public'
