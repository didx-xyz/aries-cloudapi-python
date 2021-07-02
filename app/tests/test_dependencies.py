import pytest

import dependencies

from assertpy import assert_that


def test_extract_token_from_bearer(yoma_agent):
    assert_that(yoma_agent).is_not_none()
    # assert_that(yoma_agent).is_type_of(AriesAgentController)
    assert_that(
        dependencies._extract_jwt_token_from_security_header("Bearer TOKEN")
    ).is_equal_to("TOKEN")



# controller_factorytest_headers = [
#     (
#         ControllerType.YOMA_AGENT,
#         {"x_api_key": "AdminApiKey", "x_wallet_id": "12345"},
#         AriesAgentController,
#     ),
#     (
#         ControllerType.ECOSYSTEM_AGENT,
#         {
#             "x_api_key": None,
#             "authorization_header": "Bearer 123456",
#             "x_wallet_id": "12345",
#         },
#         AriesTenantController,
#     ),
#     (
#         agent_factory.ControllerType.YOMA_AGENT,
#         {"x_api_key": "AdminApiKey", "x_wallet_id": None},
#         AriesAgentController,
#     ),
#     (
#         ControllerType.YOMA_AGENT,
#         {"authorization_header": "123456", "x_api_key": "12345", "x_wallet_id": None},
#         AriesAgentController,
#     ),
#     (
#         ControllerType.YOMA_AGENT,
#         {"x_api_key": None, "authorization_header": "Bearer 1234"},
#         False,
#     ),
#     (
#         ControllerType.ECOSYSTEM_AGENT,
#         {"authorization_header": None, "x_wallet_id": "1234"},
#         False,
#     ),
# ]


# @pytest.mark.asyncio
# @pytest.mark.parametrize(
#     "controller_type, fake_header, expected", controller_factorytest_headers
# )
# async def test_controller_factory(controller_type, fake_header, expected):
#     if expected is False:
#         with pytest.raises(HTTPException) as e:
#             utils.controller_factory(controller_type, **fake_header)
#         assert e.type == HTTPException
#         assert e.value.status_code == 401
#     else:
#         controller = utils.controller_factory(controller_type, **fake_header)
#         assert isinstance(controller, expected)


# @pytest.mark.asyncio
# @pytest.mark.parametrize(
#     "controller_type, fake_header, expected", controller_factorytest_headers
# )
# async def test_controller_factory(controller_type, fake_header, expected):
#     if expected is False:
#         with pytest.raises(HTTPException) as e:
#             utils.controller_factory(controller_type, **fake_header)
#         assert e.type == HTTPException
#         assert e.value.status_code == 401
#     else:
#         controller = utils.controller_factory(controller_type, **fake_header)
#         assert isinstance(controller, expected)