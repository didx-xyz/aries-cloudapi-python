import pytest

from app.tests.util.client import (
    yoma_client as _yoma_client,
    yoma_acapy_client as _yoma_acapy_client,
    member_admin_client as _member_admin_client,
    member_admin_acapy_client as _member_admin_acapy_client,
    ecosystem_admin_client as _ecosystem_admin_client,
    ecosystem_admin_acapy_client as _ecosystem_admin_acapy_client,
)

# YOMA


@pytest.yield_fixture(scope="module")
async def yoma_acapy_client():
    client = _yoma_acapy_client()
    yield client

    await client.close()


@pytest.yield_fixture(scope="module")
async def yoma_client():
    async with _yoma_client() as client:
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
