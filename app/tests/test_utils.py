import pytest
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from assertpy import assert_that
from fastapi import HTTPException

from agent_factory import ControllerType
import agent_factory
import utils

controller_factorytest_headers = [
    (
        ControllerType.YOMA_AGENT,
        {"x_api_key": "AdminApiKey", "x_wallet_id": "12345"},
        AriesAgentController,
    ),
    (
        ControllerType.ECOSYSTEM_AGENT,
        {
            "x_api_key": None,
            "authorization_header": "Bearer 123456",
            "x_wallet_id": "12345",
        },
        AriesTenantController,
    ),
    (
        agent_factory.ControllerType.YOMA_AGENT,
        {"x_api_key": "AdminApiKey", "x_wallet_id": None},
        AriesAgentController,
    ),
    (
        ControllerType.YOMA_AGENT,
        {"authorization_header": "123456", "x_api_key": "12345", "x_wallet_id": None},
        AriesAgentController,
    ),
    (
        ControllerType.YOMA_AGENT,
        {"x_api_key": None, "authorization_header": "Bearer 1234"},
        False,
    ),
    (
        ControllerType.ECOSYSTEM_AGENT,
        {"authorization_header": None, "x_wallet_id": "1234"},
        False,
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "controller_type, fake_header, expected", controller_factorytest_headers
)
async def test_controller_factory(controller_type, fake_header, expected):
    if expected is False:
        with pytest.raises(HTTPException) as e:
            agent_factory._controller_factory(controller_type, **fake_header)
        assert e.type == HTTPException
        assert e.value.status_code == 401
    else:
        controller = utils.controller_factory(controller_type, **fake_header)
        assert isinstance(controller, expected)


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


def test_construct_zkp_empty():
    given = [{}]
    expect = []

    result = utils.construct_zkp(given, "1234")

    assert result == expect


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


def test_extract_token_from_bearer(yoma_agent):
    assert_that(yoma_agent).is_not_none()
    assert_that(yoma_agent).is_type_of(AriesAgentController)
    assert_that(
        utils._extract_jwt_token_from_security_header("Bearer TOKEN")
    ).is_equal_to("TOKEN")


def test_yoma_agent_fixture(yoma_agent):
    assert_that(yoma_agent).is_not_none()
    assert_that(yoma_agent).is_type_of(AriesAgentController)
