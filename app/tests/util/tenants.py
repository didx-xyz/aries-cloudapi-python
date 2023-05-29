from app.admin.tenants.models import CreateTenantRequest, CreateTenantResponse
from app.tests.util.string import get_random_string
from app.util.rich_async_client import RichAsyncClient
from app.util.rich_parsing import parse_with_error_handling as parse


def append_random_string(name):
    return f"{name}_{get_random_string(7)}"


async def create_issuer_tenant(tenant_admin_client: RichAsyncClient, name: str):
    request = CreateTenantRequest(
        name=append_random_string(name), roles=["issuer"], group_id="IssuerGroup"
    )

    create_tennant_response = await tenant_admin_client.post(
        "/admin/tenants", json=request.dict()
    )

    parsed_response = parse(CreateTenantResponse, create_tennant_response.text)

    return parsed_response


async def create_verifier_tenant(tenant_admin_client: RichAsyncClient, name: str):
    request = CreateTenantRequest(
        name=append_random_string(name),
        roles=["verifier"],
        group_id="VerifierGroup",
    )

    create_tennant_response = await tenant_admin_client.post(
        "/admin/tenants", json=request.dict()
    )

    if create_tennant_response.is_error:
        raise Exception(
            f"Could not create verifier tenant. {create_tennant_response.text}"
        )

    parsed_response = parse(CreateTenantResponse, create_tennant_response.text)

    return parsed_response


async def create_tenant(tenant_admin_client: RichAsyncClient, name: str):
    request = CreateTenantRequest(
        image_url="https://aries.ca/images/sample.png",
        name=append_random_string(name),
        group_id="TenantGroup",
    )

    create_tennant_response = await tenant_admin_client.post(
        "/admin/tenants", json=request.dict()
    )
    parsed_response = parse(CreateTenantResponse, create_tennant_response.text)

    return parsed_response


async def delete_tenant(admin_client: RichAsyncClient, tenant_id: str):
    await admin_client.delete(f"/admin/tenants/{tenant_id}")
