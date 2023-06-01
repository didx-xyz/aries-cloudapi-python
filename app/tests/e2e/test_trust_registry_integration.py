import pytest

from app.facades.trust_registry import actor_by_id
from app.listener import Listener
from app.tests.util.client import get_tenant_admin_client, get_tenant_client
from app.tests.util.string import base64_to_json, random_string
from app.tests.util.tenants import (
    create_issuer_tenant,
    create_tenant,
    create_verifier_tenant,
    delete_tenant,
)
from app.util.rich_async_client import RichAsyncClient


@pytest.mark.anyio
async def test_accept_proof_request_verifier_no_public_did(
    governance_client: RichAsyncClient,
):
    tenant_admin = get_tenant_admin_client()

    # Create tenants
    verifier_tenant = await create_verifier_tenant(tenant_admin, "acme")
    issuer_tenant = await create_issuer_tenant(tenant_admin, "this-is-it")
    holder_tenant = await create_tenant(tenant_admin, "alice")

    # Get clients
    verifier_client = get_tenant_client(token=verifier_tenant.access_token)
    issuer_client = get_tenant_client(token=issuer_tenant.access_token)
    holder_client = get_tenant_client(token=holder_tenant.access_token)

    # Create connection between issuer and holder
    invitation = (
        await issuer_client.post("/generic/connections/create-invitation")
    ).json()

    issuer_tenant_listener = Listener(
        topic="connections", wallet_id=issuer_tenant.tenant_id
    )

    invitation_response = (
        await holder_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    issuer_holder_connection_id = invitation["connection_id"]
    holder_issuer_connection_id = invitation_response["connection_id"]

    await issuer_tenant_listener.wait_for_filtered_event(
        filter_map={"state": "completed", "connection_id": issuer_holder_connection_id}
    )
    issuer_tenant_listener.stop()

    # Create connection between holder and verifier
    # We need to use the multi-use didcomm invitation from the trust registry
    verifier_actor = await actor_by_id(verifier_tenant.tenant_id)

    assert verifier_actor

    verifier_tenant_listener = Listener(
        topic="connections",
        wallet_id=verifier_tenant.tenant_id,
    )

    assert verifier_actor["didcomm_invitation"]

    invitation_json = base64_to_json(
        verifier_actor["didcomm_invitation"].split("?oob=")[1]
    )
    invitation_response = (
        await holder_client.post(
            "/generic/oob/accept-invitation",
            json={"invitation": invitation_json},
        )
    ).json()

    payload = await verifier_tenant_listener.wait_for_filtered_event(
        filter_map={"state": "completed"}, timeout=100
    )
    verifier_tenant_listener.stop()

    holder_verifier_connection_id = invitation_response["connection_id"]
    verifier_holder_connection_id = payload["connection_id"]

    # Create schema as governance
    schema = (
        await governance_client.post(
            "/generic/definitions/schemas",
            json={
                "name": "e2e-flow",
                "version": "1.0.0",
                "attribute_names": ["name", "age"],
            },
        )
    ).json()

    schema_id = schema["id"]

    # Create credential definition as issuer
    credential_definition = await issuer_client.post(
        "/generic/definitions/credentials",
        json={
            "tag": random_string(5),
            "schema_id": schema_id,
            "support_revocation": True,
        },
    )

    if credential_definition.is_client_error:
        raise Exception(credential_definition.json()["detail"])

    credential_definition_id = credential_definition.json()["id"]

    # Issue credential from issuer to holder
    holder_tenant_listener = Listener(
        topic="credentials", wallet_id=holder_tenant.tenant_id
    )

    issuer_credential_exchange = (
        await issuer_client.post(
            "/generic/issuer/credentials",
            json={
                "protocol_version": "v1",
                "connection_id": issuer_holder_connection_id,
                "credential_definition_id": credential_definition_id,
                "attributes": {"name": "Alice", "age": "44"},
            },
        )
    ).json()

    payload = await holder_tenant_listener.wait_for_filtered_event(
        filter_map={
            "state": "offer-received",
            "connection_id": holder_issuer_connection_id,
        },
    )
    holder_tenant_listener.stop()

    issuer_credential_exchange_id = issuer_credential_exchange["credential_id"]
    holder_credential_exchange_id = payload["credential_id"]

    issuer_tenant_cred_listener = Listener(
        topic="credentials", wallet_id=issuer_tenant.tenant_id
    )

    response = await holder_client.post(
        f"/generic/issuer/credentials/{holder_credential_exchange_id}/request"
    )

    # Wait for credential exchange to finish
    await issuer_tenant_cred_listener.wait_for_filtered_event(
        filter_map={"state": "done", "credential_id": issuer_credential_exchange_id},
        timeout=300,
    )
    issuer_tenant_cred_listener.stop()

    # Present proof from holder to verifier

    holder_tenant_proofs_listener = Listener(
        topic="proofs", wallet_id=holder_tenant.tenant_id
    )

    response = await verifier_client.post(
        "/generic/verifier/send-request",
        json={
            "protocol_version": "v1",
            "connection_id": verifier_holder_connection_id,
            "proof_request": {
                "name": "Age Check",
                "version": "1.0",
                "requested_attributes": {
                    "name": {
                        "name": "name",
                        "restrictions": [{"cred_def_id": credential_definition_id}],
                    }
                },
                "requested_predicates": {
                    "age_over_21": {
                        "name": "age",
                        "p_type": ">=",
                        "p_value": "21",
                        "restrictions": [{"cred_def_id": credential_definition_id}],
                    }
                },
            },
        },
    )

    verifier_proof_exchange = response.json()

    payload = await holder_tenant_proofs_listener.wait_for_filtered_event(
        filter_map={
            "state": "request-received",
            "connection_id": holder_verifier_connection_id,
        },
        timeout=300,
    )
    holder_tenant_proofs_listener.stop()

    verifier_proof_exchange_id = verifier_proof_exchange["proof_id"]
    holder_proof_exchange_id = payload["proof_id"]

    available_credentials = (
        await holder_client.get(
            f"/generic/verifier/proofs/{holder_proof_exchange_id}/credentials",
        )
    ).json()

    cred_id = available_credentials[0]["cred_info"]["referent"]

    verifier_tenant_proofs_listener = Listener(
        topic="proofs", wallet_id=verifier_tenant.tenant_id
    )

    response = await holder_client.post(
        "/generic/verifier/accept-request",
        json={
            "proof_id": holder_proof_exchange_id,
            "presentation_spec": {
                "requested_attributes": {
                    "name": {
                        "cred_id": cred_id,
                        "revealed": True,
                    }
                },
                "requested_predicates": {"age_over_21": {"cred_id": cred_id}},
                "self_attested_attributes": {},
            },
        },
    )

    await verifier_tenant_proofs_listener.wait_for_filtered_event(
        filter_map={
            "state": "done",
            "proof_id": verifier_proof_exchange_id,
            "verified": True,
        },
        timeout=300,
    )
    verifier_tenant_proofs_listener.stop()

    # Delete all tenants
    await delete_tenant(tenant_admin, issuer_tenant.tenant_id)
    await delete_tenant(tenant_admin, verifier_tenant.tenant_id)
    await delete_tenant(tenant_admin, holder_tenant.tenant_id)
