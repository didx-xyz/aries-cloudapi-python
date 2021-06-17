# from app.utils import construct_zkp
import pytest
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException
import utils
import json

testheaders = [
    ({"api_key": "AdminApiKey", "tenant_jwt": "123456", "wallet_id": "12345"}, "admin"),
    ({"tenant_jwt": "123456", "wallet_id": "12345"}, "tenant"),
    ({"api_key": "AdminApiKey"}, "admin"),
    ({"kjnc": "AdminApiKey"}, None),
    ({"tenant_jwt": "123456", "api_key": "12345"}, "admin"),
    ({"tenant_jwt": "123456"}, None),
    ({"wallet_id": "123456"}, None),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("fake_header,expected", testheaders)
async def test_get_controller_type(fake_header, expected):
    assert utils.get_controller_type(fake_header) == expected


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


def test_construct_zkp():
    given = [[{"name": "name", "p_type": ">=", "p_value": "21"}], "abcde:test:0.0.1"]
    expected = [
        {
            "name": "name",
            "p_type": ">=",
            "p_value": "21",
            "restrictions": [{"schema_id": "abcde:test:0.0.1"}],
        }
    ]

    result = utils.construct_zkp(*given)

    assert result == expected


def test_construct_indy_proof_request():
    given = [
        "abcde",
        "abcde:test:0.0.1",
        [{"name": "name"}, {"name": "age"}],
        [{"name": "name", "p_type": ">=", "p_value": "21"}],
    ]

    expected = {
        "name": "abcde",
        "requested_attributes": {
            "0_age_uuid": {"name": "age"},
            "0_name_uuid": {"name": "name"},
        },
        "requested_predicates": {
            "0_name_GE_uuid": {"name": "name", "p_type": ">=", "p_value": "21"}
        },
        "version": "0.0.1",
    }

    result = utils.construct_indy_proof_request(*given)

    assert result == expected
