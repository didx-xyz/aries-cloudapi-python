import pytest

from app.event_handling.sse_listener import SseListener
from app.models.definitions import CredentialSchema
from app.routes.admin.tenants import router
from app.routes.connections import router as conn_router
from app.routes.definitions import router as def_router
from app.routes.issuer import router as issuer_router
from app.tests.util.client import get_tenant_client
from shared import RichAsyncClient

TENANTS_BASE_PATH = router.prefix
CONNECTIONS_BASE_PATH = conn_router.prefix
DEFINITIONS_BASE_PATH = def_router.prefix
ISSUER_BASE_PATH = issuer_router.prefix


@pytest.mark.anyio
async def test_extra_settings(
    tenant_admin_client: RichAsyncClient, schema_definition: CredentialSchema
):
    issuer_response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "wallet_label": "local_issuer",
            "wallet_name": "EpicGamer",
            "roles": ["issuer", "verifier"],
            "group_id": "PerTenant",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
        },
    )
    assert issuer_response.status_code == 200
    issuer = issuer_response.json()

    holder_response = await tenant_admin_client.post(
        TENANTS_BASE_PATH,
        json={
            "wallet_label": "local_holder",
            "wallet_name": "EpicHolder",
            "group_id": "PerTenant",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
            "extra_settings": {"ACAPY_LOG_LEVEL": "debug"},
        },
    )
    assert holder_response.status_code == 200
    holder = holder_response.json()
    print("Issuer ==> ", issuer)
    print("Holder ==> ", holder)

    issuer_client = get_tenant_client(token=issuer["access_token"])
    holder_client = get_tenant_client(token=holder["access_token"])

    print("***Onboarded***")

    invitation = (
        await issuer_client.post(CONNECTIONS_BASE_PATH + "/create-invitation")
    ).json()

    issuer_tenant_listener = SseListener(
        topic="connections", wallet_id=issuer["wallet_id"]
    )

    invitation_response = (
        await holder_client.post(
            CONNECTIONS_BASE_PATH + "/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    issuer_holder_connection_id = invitation["connection_id"]
    holder_issuer_connection_id = invitation_response["connection_id"]

    await issuer_tenant_listener.wait_for_event(
        field="connection_id",
        field_id=issuer_holder_connection_id,
        desired_state="completed",
    )
    print("***Connection Made***")
    cred_def = (
        await issuer_client.post(
            DEFINITIONS_BASE_PATH + "/credentials",
            json={
                "tag": "PerTenant",
                "schema_id": schema_definition.id,
                "support_revocation": False,
            },
        )
    ).json()

    holder_tenant_listener = SseListener(
        topic="credentials", wallet_id=holder["wallet_id"]
    )

    issuer_credential_exchange = (
        await issuer_client.post(
            f"{ISSUER_BASE_PATH}",
            json={
                "protocol_version": "v1",
                "connection_id": issuer_holder_connection_id,
                "indy_credential_detail": {
                    "credential_definition_id": cred_def["id"],
                    "attributes": {"speed": "9001"},
                },
            },
        )
    ).json()

    payload = await holder_tenant_listener.wait_for_event(
        field="connection_id",
        field_id=holder_issuer_connection_id,
        desired_state="offer-received",
    )

    issuer_credential_exchange_id = issuer_credential_exchange["credential_id"]
    holder_credential_exchange_id = payload["credential_id"]

    issuer_tenant_cred_listener = SseListener(
        topic="credentials", wallet_id=issuer["wallet_id"]
    )

    response = await holder_client.post(
        f"{ISSUER_BASE_PATH}/{holder_credential_exchange_id}/request"
    )
    print("***Cred requested***")
    # Wait for credential exchange to finish
    await issuer_tenant_cred_listener.wait_for_event(
        field="credential_id",
        field_id=issuer_credential_exchange_id,
        desired_state="done",
    )

    assert response.status_code == 200
    assert False

    # TODO test extra setting work
    # TODO remove wallets after test done
