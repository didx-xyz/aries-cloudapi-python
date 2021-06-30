import pytest
from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import HTTPException
import facade
from utils import controller_factory, ControllerType

testheaders = [
    (facade.yoma_agent, {"x_api_key": "AdminApiKey"}, "123456", AriesAgentController),
    (
        facade.ecosystem_agent,
        {"authorization": "Bearer 344352dfsg"},
        "344352dfsg",
        AriesTenantController,
    ),
    (
        facade.member_agent,
        {"x_api_key": "AdminApiKey", "authorization": "Bearer kjalsdkfjasi3l"},
        "kjalsdkfjasi3l",
        AriesTenantController,
    ),
]


async def async_next(param):
    async for item in param:
        return item
    else:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "factory, fake_header, expected_token, expected_type", testheaders
)
async def test_create_controller(factory, fake_header, expected_token, expected_type):
    if expected_type:
        controller = await async_next(factory(**fake_header))
        assert type(controller) is expected_type
        if type(controller) is AriesTenantController:
            assert controller.tenant_jwt == expected_token
        elif type(controller) is AriesAgentController:
            assert controller.api_key == fake_header["x_api_key"]
