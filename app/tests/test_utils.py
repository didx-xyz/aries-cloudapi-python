import pytest
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException
import utils

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
@pytest.mark.parametrize("fake_header,expected", testheaders)
async def test_validate_auth_header(fake_header, expected):
    assert utils.validate_auth_header(fake_header) == expected


controller_factorytest_headers = [
    (
        {"api_key": "AdminApiKey", "tenant_jwt": "123456", "wallet_id": "12345"},
        type(AriesAgentController),
    ),
    ({"tenant_jwt": "123456", "wallet_id": "12345"}, type(AriesTenantController)),
    ({"api_key": "AdminApiKey"}, type(AriesAgentController)),
    ({"kjnc": "AdminApiKey"}, False),
    ({"tenant_jwt": "123456", "api_key": "12345"}, type(AriesAgentController)),
    ({"tenant_jwt": "123456"}, False),
    ({"wallet_id": "123456"}, False),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fake_header, expected", controller_factorytest_headers)
async def test_controller_factory(fake_header, expected):
    if expected is False:
        with pytest.raises(HTTPException) as e:
            utils.controller_factory(fake_header)
        assert e.type == HTTPException
        assert e.value.status_code == 400
        assert (
            "Bad headers. Either provide an api_key or both wallet_id and tenant_jwt"
            in e.value.detail
        )
    else:
        controller = utils.controller_factory(fake_header)
        assert isinstance(type(controller), expected)
