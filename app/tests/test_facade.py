import pytest
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException
import facade


testheaders = [
    ({"api_key": "AdminApiKey", "tenant_jwt": "123456", "wallet_id": "12345"}, "admin"),
    ({"api_key": None, "tenant_jwt": "123456", "wallet_id": "12345"}, "tenant"),
    ({"api_key": "AdminApiKey", "tenant_jwt": None, "wallet_id": None}, "admin"),
    ({"api_key": "abcde", "tenant_jwt": "abcde", "wallet_id": None}, "admin"),
    ({"api_key": None, "tenant_jwt": "123456", "wallet_id": None}, False),
    ({"api_key": None, "tenant_jwt": None, "wallet_id": "12345"}, False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fake_header, expected", testheaders)
async def test_create_controller(fake_header, expected):
    if expected:
        async with facade.create_controller(fake_header) as controller:
            pass
        if fake_header["api_key"]:
            assert type(controller) is AriesAgentController
        else:
            assert type(controller) is AriesTenantController
    else:
        with pytest.raises(HTTPException) as e:
            async with facade.create_controller(fake_header) as controller:
                pass
        assert pytest.raises(HTTPException)
        assert e.type == HTTPException
        assert e.value.status_code == 400
        assert (
            "Bad headers. Either provide an api_key or both wallet_id and tenant_jwt"
            in e.value.detail
        )
