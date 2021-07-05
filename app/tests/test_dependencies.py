import pytest
from fastapi import HTTPException
from contextlib import asynccontextmanager

import dependencies

from assertpy import assert_that


def test_extract_token_from_bearer(yoma_agent):
    assert_that(yoma_agent).is_not_none()
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

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.member_admin_agent)() as c:
            assert c is None


@pytest.mark.asyncio
async def test_ecosystem_admin_agent():
    async with asynccontextmanager(dependencies.ecosystem_admin_agent)(
        x_api_key="adminApiKey"
    ) as c:
        assert c is not None
        assert c.api_key == "adminApiKey"

    with pytest.raises(HTTPException):
        async with asynccontextmanager(dependencies.ecosystem_admin_agent)() as c:
            assert c is None
