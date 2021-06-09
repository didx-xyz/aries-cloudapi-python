import pytest
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException
import facade


testheaders = [
    ({"api_key": "AdminApiKey", "tenant_jwt": "123456", "wallet_id": "12345"}, True),
    ({"tenant_jwt": "123456", "wallet_id": "12345"}, True),
    ({"api_key": "AdminApiKey"}, True),
    ({"kjnc": "AdminApiKey"}, False),
    ({"tenant_jwt": "123456", "api_key": "12345"}, True),
    ({"tenant_jwt": "123456"}, False),
    ({"wallet_id": "123456"}, False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fake_header, expected", testheaders)
async def test_create_controller(fake_header, expected):
    if expected:
        async with facade.create_controller(fake_header) as controller:
            pass
        if "api_key" in fake_header:
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
