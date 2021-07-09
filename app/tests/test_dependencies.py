import pytest
from aries_cloudcontroller import AriesTenantController
from fastapi import HTTPException
from contextlib import asynccontextmanager

import dependencies

from assertpy import assert_that


def test_extract_token_from_bearer():
    # assert_that(yoma_agent).is_type_of(AriesAgentController)
    assert_that(
        dependencies._extract_jwt_token_from_security_header("Bearer TOKEN")
    ).is_equal_to("TOKEN")


@pytest.mark.asyncio
async def test_yoma_agent():
    async with asynccontextmanager(dependencies.yoma_agent)(
        x_api_key="adminApiKey"
    ) as c:
        assert c is not None
        assert c.api_key == "adminApiKey"

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.yoma_agent)() as c:
            assert c is None


@pytest.mark.asyncio
async def test_ecosystem_agent():
    async with asynccontextmanager(dependencies.ecosystem_agent)(
        x_api_key="adminApiKey", authorization="Bearer 12345", x_wallet_id="12345"
    ) as c:
        assert c is not None
        assert c.tenant_jwt == "12345"

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.ecosystem_agent)() as c:
            assert c is None


@pytest.mark.asyncio
async def test_member_agent():
    async with asynccontextmanager(dependencies.member_agent)(
        authorization="Bearer 12345", x_wallet_id="12345"
    ) as c:
        assert c is not None
        assert c.tenant_jwt == "12345"

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.member_agent)() as c:
            assert c is None


@pytest.mark.asyncio
async def test_member_admin_agent():
    async with asynccontextmanager(dependencies.member_admin_agent)(
        x_api_key="adminApiKey"
    ) as c:
        assert c is not None
        assert c.api_key == "adminApiKey"
        assert c.multitenant is not None

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.member_admin_agent)() as c:
            assert c is None


async def async_next(param):
    async for item in param:
        return item
    else:  # NOSONAR
        return None


@pytest.mark.asyncio
async def test_member_or_ecosystem_agent():
    # apologies fro the use of async_next... maybe we should just add the async context manager to these methods
    # even though fastapi does that for us. I'd assume it will play nice if they are already there.
    # then we can at least have a consistency of calling pattern. tests can use as is. WE don't have to wrap.
    # maybe create another ticket to look at this.
    with pytest.raises(HTTPException) as e:
        await async_next(
            dependencies.ecosystem_or_member_agent(
                x_api_key="apikey", authorization="Bearer x"
            )
        )
    assert e.value.status_code == 400
    assert e.value.detail == "invalid role"
    ecosystem_agent_url = dependencies.ECOSYSTEM_AGENT_URL
    member_agent_url = dependencies.MEMBER_AGENT_URL
    dependencies.ECOSYSTEM_AGENT_URL = "eco-system-agent-url"
    dependencies.MEMBER_AGENT_URL = "member-agent-url"

    c = await async_next(
        dependencies.ecosystem_or_member_agent(
            x_api_key="apikey", authorization="Bearer x", x_role="ecosystem"
        )
    )
    assert type(c) == AriesTenantController
    assert c.admin_url == "eco-system-agent-url"

    c = await async_next(
        dependencies.ecosystem_or_member_agent(
            x_api_key="apikey", authorization="Bearer x", x_role="member"
        )
    )
    assert type(c) == AriesTenantController
    assert c.admin_url == "member-agent-url"


@pytest.mark.asyncio
async def test_ecosystem_admin_agent():
    async with asynccontextmanager(dependencies.ecosystem_admin_agent)(
        x_api_key="adminApiKey"
    ) as c:
        assert c is not None
        assert c.api_key == "adminApiKey"
        assert c.multitenant is not None

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.ecosystem_admin_agent)() as c:
            assert c is None
