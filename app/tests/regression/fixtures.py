from dataclasses import dataclass
from typing import Any, AsyncGenerator

import pytest

from app.dependencies.auth import (
    AcaPyAuthVerified,
    acapy_auth_from_header,
    acapy_auth_verified,
)
from app.models.definitions import (
    CreateCredentialDefinition,
    CreateSchema,
    CredentialSchema,
)
from app.models.tenants import CreateTenantRequest, CreateTenantResponse
from app.routes.connections import router as conn_router
from app.routes.definitions import create_credential_definition, create_schema
from app.tests.util.client import get_tenant_admin_client, get_tenant_client
from app.tests.util.tenants import TENANT_BASE_PATH, post_tenant_request
from app.tests.util.trust_registry import register_issuer
from app.tests.util.webhooks import check_webhook_state
from app.util.string import random_version
from shared.util.rich_async_client import RichAsyncClient

CONNECTIONS_BASE_PATH = conn_router.prefix

regression_tests_group_id = "RegressionTests"


async def get_or_create_tenant(
    admin_client: RichAsyncClient, name: str, roles: list[str] = []
) -> CreateTenantResponse:
    # Fetch all tenants in the regression test group
    list_tenants = (
        await admin_client.get(
            TENANT_BASE_PATH, params={"group_id": regression_tests_group_id}
        )
    ).json()

    # Try to find the tenant by the specific role or name
    for tenant in list_tenants:
        if tenant["wallet_label"] == name:
            return tenant  # Return existing tenant if found

    # If not found, create a new tenant
    request = CreateTenantRequest(
        wallet_label=name,
        group_id=regression_tests_group_id,
        roles=roles,
    )
    return await post_tenant_request(admin_client, request)


@pytest.fixture(scope="session")
async def holder_tenant() -> AsyncGenerator[CreateTenantResponse, Any]:
    async with get_tenant_admin_client() as admin_client:
        tenant = await get_or_create_tenant(
            admin_client, "RegressionTestHolder", roles=[]
        )
        yield tenant


@pytest.fixture(scope="session")
async def issuer_tenant() -> AsyncGenerator[CreateTenantResponse, Any]:
    async with get_tenant_admin_client() as admin_client:
        tenant = await get_or_create_tenant(
            admin_client, "RegressionTestIssuer", roles=["issuer"]
        )
        yield tenant


@pytest.fixture(scope="session")
async def verifier_tenant() -> AsyncGenerator[CreateTenantResponse, Any]:
    async with get_tenant_admin_client() as admin_client:
        tenant = await get_or_create_tenant(
            admin_client, "RegressionTestVerifier", roles=["verifier"]
        )
        yield tenant


@pytest.fixture(scope="function")
async def holder_client(
    holder_tenant: CreateTenantResponse,
) -> AsyncGenerator[RichAsyncClient, Any]:
    async with get_tenant_client(
        token=holder_tenant.access_token
    ) as holder_async_client:
        yield holder_async_client


@pytest.fixture(scope="module")
async def issuer_client(
    issuer_tenant: CreateTenantResponse,
) -> AsyncGenerator[RichAsyncClient, Any]:
    async with get_tenant_client(
        token=issuer_tenant.access_token
    ) as faber_async_client:
        yield faber_async_client


@pytest.fixture(scope="function")
async def verifier_client(
    verifier_tenant: CreateTenantResponse,
) -> AsyncGenerator[RichAsyncClient, Any]:
    async with get_tenant_client(
        token=verifier_tenant.access_token
    ) as acme_async_client:
        yield acme_async_client


@dataclass
class IssuerHolderConnection:
    holder_connection_id: str
    issuer_connection_id: str


@pytest.fixture(scope="function")
async def issuer_holder_connection(
    holder_client: RichAsyncClient, issuer_client: RichAsyncClient
) -> IssuerHolderConnection:
    # create invitation on faber side
    invitation = (
        await issuer_client.post(f"{CONNECTIONS_BASE_PATH}/create-invitation")
    ).json()

    # accept invitation on alice side
    invitation_response = (
        await holder_client.post(
            f"{CONNECTIONS_BASE_PATH}/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    issuer_connection_id = invitation["connection_id"]
    holder_connection_id = invitation_response["connection_id"]

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    assert await check_webhook_state(
        holder_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": holder_connection_id,
        },
        look_back=5,
    )
    assert await check_webhook_state(
        issuer_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": issuer_connection_id,
        },
        look_back=5,
    )

    return IssuerHolderConnection(
        holder_connection_id=holder_connection_id,
        issuer_connection_id=issuer_connection_id,
    )


@pytest.fixture(scope="session")
async def schema_definition_regression_test(
    mock_governance_auth: AcaPyAuthVerified,
) -> CredentialSchema:
    definition = CreateSchema(
        name="test_schema_alt", version=random_version(), attribute_names=["speed"]
    )

    schema_definition_result = await create_schema(definition, mock_governance_auth)

    return schema_definition_result


@pytest.fixture(scope="module")
async def credential_definition_id_revocable_regression_test(
    schema_definition_regression_test: CredentialSchema,  # pylint: disable=redefined-outer-name
    issuer_client: RichAsyncClient,
) -> str:
    await register_issuer(issuer_client, schema_definition_regression_test.id)

    definition = CreateCredentialDefinition(
        tag="tag",
        schema_id=schema_definition_regression_test.id,
        support_revocation=True,
        revocation_registry_size=2000,
    )

    auth = acapy_auth_verified(
        acapy_auth_from_header(issuer_client.headers["x-api-key"])
    )
    result = await create_credential_definition(
        credential_definition=definition, auth=auth
    )

    return result.id
