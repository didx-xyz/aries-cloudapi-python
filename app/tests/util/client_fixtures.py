import pytest

from app.tests.util.client import (
    governance_client as _governance_client,
    governance_acapy_client as _governance_acapy_client,
    member_admin_client as _member_admin_client,
    member_admin_acapy_client as _member_admin_acapy_client,
    ecosystem_admin_client as _ecosystem_admin_client,
    ecosystem_admin_acapy_client as _ecosystem_admin_acapy_client,
)

# governance


@pytest.yield_fixture(scope="module")
async def governance_acapy_client():
    client = _governance_acapy_client()
    yield client

    await client.close()


@pytest.yield_fixture(scope="module")
async def governance_client():
    async with _governance_client() as client:
        yield client


# MEMBER ADMIN


@pytest.yield_fixture(scope="module")
async def member_admin_client():
    async with _member_admin_client() as client:
        yield client


@pytest.yield_fixture(scope="module")
async def member_admin_acapy_client():
    client = _member_admin_acapy_client()
    yield client

    await client.close()


# Ecosystem Admin


@pytest.yield_fixture(scope="module")
async def ecosystem_admin_client():
    async with _ecosystem_admin_client() as client:
        yield client


@pytest.yield_fixture(scope="module")
async def ecosystem_admin_acapy_client():
    client = _ecosystem_admin_acapy_client()
    yield client

    await client.close()
