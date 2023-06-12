from contextlib import asynccontextmanager

import fastapi
import pytest
from aries_cloudcontroller import AcaPyClient
from fastapi import APIRouter, Depends
from httpx import AsyncClient

from app.main import app
from shared import CLOUDAPI_URL, GOVERNANCE_ACAPY_API_KEY, TENANT_ACAPY_API_KEY
from shared.dependencies.auth import (
    AcaPyAuth,
    Role,
    admin_agent_selector,
    agent_role,
    agent_selector,
)

TEST_BEARER_HEADER = "Bearer x"
TEST_BEARER_HEADER_2 = "Bearer Y"
BEARER_TOKEN = "12345"


@pytest.mark.anyio
async def test_governance_agent():
    async with asynccontextmanager(agent_selector)(
        auth=AcaPyAuth(role=Role.GOVERNANCE, token=GOVERNANCE_ACAPY_API_KEY)
    ) as c:
        assert isinstance(c, AcaPyClient)
        assert c.base_url == Role.GOVERNANCE.agent_type.base_url
        assert c.client.headers["x-api-key"] == GOVERNANCE_ACAPY_API_KEY
        assert "Authorization" not in c.client.headers


@pytest.mark.anyio
async def test_tenant_agent():
    async with asynccontextmanager(agent_role(Role.TENANT))(
        AcaPyAuth(role=Role.TENANT, token=BEARER_TOKEN)
    ) as c:
        assert isinstance(c, AcaPyClient)
        assert c.base_url == Role.TENANT.agent_type.base_url
        assert c.client.headers["Authorization"] == f"Bearer {BEARER_TOKEN}"
        assert c.client.headers["x-api-key"] == TENANT_ACAPY_API_KEY


async def async_next(param):
    async for item in param:
        return item
    else:  # NOSONAR
        return None


@pytest.mark.anyio
async def test_agent_selector():
    c = await async_next(agent_selector(AcaPyAuth(token="apiKey", role=Role.TENANT)))
    assert isinstance(c, AcaPyClient)
    assert c.base_url == Role.TENANT.agent_type.base_url

    c = await async_next(
        agent_selector(AcaPyAuth(token="apiKey", role=Role.GOVERNANCE))
    )
    assert isinstance(c, AcaPyClient)
    assert c.base_url == Role.GOVERNANCE.agent_type.base_url


@pytest.mark.anyio
async def test_admin_agent_selector():
    c = await async_next(
        admin_agent_selector(AcaPyAuth(token="apiKey", role=Role.TENANT_ADMIN))
    )
    assert isinstance(c, AcaPyClient)
    assert c.base_url == Role.TENANT.agent_type.base_url
    assert c.client.headers["x-api-key"] == "apiKey"
    assert "Authorization" not in c.client.headers

    c = await async_next(
        admin_agent_selector(AcaPyAuth(token="apiKey", role=Role.GOVERNANCE))
    )
    assert isinstance(c, AcaPyClient)
    assert c.base_url == Role.GOVERNANCE.agent_type.base_url
    assert c.client.headers["x-api-key"] == "apiKey"
    assert "Authorization" not in c.client.headers

    with pytest.raises(fastapi.exceptions.HTTPException):
        await async_next(
            admin_agent_selector(AcaPyAuth(token="apiKey", role=Role.TENANT))
        )


@pytest.mark.anyio
async def test_web_tenant():
    # Test adds two methods to the router it creates (/testabc) - called this to make
    # sure it doesn't interfere with normal operation
    # this method then saves the injected agent and then the test validates the injected
    # agent is injected as it expects.

    # a parameterised test might be a better way to go - I'm not sure. Parameterised tests can be quite opaque
    # sometimes

    router = APIRouter(prefix="/testsabc")

    injected_controller = None

    @router.get("/admin")
    async def call_admin(
        aries_controller: AcaPyClient = Depends(admin_agent_selector),
    ):
        nonlocal injected_controller
        injected_controller = aries_controller

    @router.get("")
    async def call(
        aries_controller: AcaPyClient = Depends(agent_selector),
    ):
        nonlocal injected_controller
        injected_controller = aries_controller

    app.include_router(router)

    async def make_call(route_suffix: str = "", headers=None):
        async with AsyncClient(app=app, base_url=CLOUDAPI_URL) as ac:
            response = await ac.get("/testsabc" + route_suffix, headers={**headers})
            return response

    # default (non admin) agents
    # when
    response = await make_call(headers={})
    # then
    assert response.status_code == 403
    assert response.text == '{"detail":"Not authenticated"}'

    # # when
    await make_call(
        headers={
            "x-api-key": "governance.ADDASDFDFF",
        }
    )
    # then
    assert injected_controller.base_url == Role.GOVERNANCE.agent_type.base_url
    assert injected_controller.client.headers["x-api-key"] == "ADDASDFDFF"
    assert isinstance(injected_controller, AcaPyClient)

    # when
    await make_call(headers={"x-api-key": f"tenant.{TEST_BEARER_HEADER}"})
    # then
    assert injected_controller.base_url == Role.TENANT.agent_type.base_url
    assert (
        injected_controller.client.headers["Authorization"]
        == f"Bearer {TEST_BEARER_HEADER}"
    )
    assert (
        injected_controller.client.headers["x-api-key"]
        == Role.TENANT.agent_type.x_api_key
    )
    assert isinstance(injected_controller, AcaPyClient)

    # admin agents
    # when (no authentication)
    response = await make_call(headers={}, route_suffix="/admin")
    # then
    assert response.status_code == 403
    assert response.text == '{"detail":"Not authenticated"}'

    # when (incorrect role)
    response = await make_call(
        headers={"x-api-key": "some.adminApiKey"}, route_suffix="/admin"
    )
    # then
    assert response.status_code == 401
    assert "Unauthorized" in response.text

    # when
    await make_call(
        route_suffix="/admin",
        headers={"x-api-key": "governance.ADDASDFDFF"},
    )
    # then
    assert injected_controller.base_url == Role.GOVERNANCE.agent_type.base_url
    assert injected_controller.client.headers["x-api-key"] == "ADDASDFDFF"
    assert isinstance(injected_controller, AcaPyClient)

    # when
    await make_call(
        route_suffix="/admin",
        headers={
            "x-api-key": "tenant-admin.provided-api-key",
        },
    )
    # then
    assert injected_controller.base_url == Role.TENANT.agent_type.base_url
    assert injected_controller.client.headers["x-api-key"] == "provided-api-key"
    assert isinstance(injected_controller, AcaPyClient)


@pytest.mark.anyio
async def test_tenant_admin_agent():
    async with asynccontextmanager(agent_role(role=Role.TENANT_ADMIN))(
        auth=AcaPyAuth(role=Role.TENANT_ADMIN, token=TENANT_ACAPY_API_KEY)
    ) as c:
        assert isinstance(c, AcaPyClient)
        assert c.client.headers["x-api-key"] == TENANT_ACAPY_API_KEY
        assert "Authorization" not in c.client.headers
