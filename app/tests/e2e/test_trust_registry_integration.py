import pytest

from app.admin.tenants.models import CreateTenantResponse
from app.event_handling.sse_listener import SseListener
from app.facades.trust_registry import actor_by_id
from app.tests.util.client import get_tenant_client
from app.tests.util.string import base64_to_json, random_string
from shared import RichAsyncClient


@pytest.mark.anyio
async def test_accept_proof_request_verifier_no_public_did(
    governance_client: RichAsyncClient,
    acme_verifier: CreateTenantResponse,
    faber_issuer: CreateTenantResponse,
    alice_tenant: CreateTenantResponse,
):
    # Get clients
    verifier_client = get_tenant_client(token=acme_verifier.access_token)
    issuer_client = get_tenant_client(token=faber_issuer.access_token)
    holder_client = get_tenant_client(token=alice_tenant.access_token)

    # Create connection between issuer and holder
    invitation = (
        await issuer_client.post("/generic/connections/create-invitation")
    ).json()

    issuer_tenant_listener = SseListener(
        topic="connections", wallet_id=faber_issuer.tenant_id
    )

    invitation_response = (
        await holder_client.post(
            "/generic/connections/accept-invitation",
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

    # Create connection between holder and verifier
    # We need to use the multi-use didcomm invitation from the trust registry
    verifier_actor = await actor_by_id(acme_verifier.tenant_id)

    assert verifier_actor

    verifier_tenant_listener = SseListener(
        topic="connections",
        wallet_id=acme_verifier.tenant_id,
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

    payload = await verifier_tenant_listener.wait_for_state(desired_state="completed")

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
    holder_tenant_listener = SseListener(
        topic="credentials", wallet_id=alice_tenant.tenant_id
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

    payload = await holder_tenant_listener.wait_for_event(
        field="connection_id",
        field_id=holder_issuer_connection_id,
        desired_state="offer-received",
    )

    issuer_credential_exchange_id = issuer_credential_exchange["credential_id"]
    holder_credential_exchange_id = payload["credential_id"]

    issuer_tenant_cred_listener = SseListener(
        topic="credentials", wallet_id=faber_issuer.tenant_id
    )

    response = await holder_client.post(
        f"/generic/issuer/credentials/{holder_credential_exchange_id}/request"
    )

    # Wait for credential exchange to finish
    await issuer_tenant_cred_listener.wait_for_event(
        field="credential_id",
        field_id=issuer_credential_exchange_id,
        desired_state="done",
    )

    # Present proof from holder to verifier

    holder_tenant_proofs_listener = SseListener(
        topic="proofs", wallet_id=alice_tenant.tenant_id
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

    payload = await holder_tenant_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=holder_verifier_connection_id,
        desired_state="request-received",
    )

    verifier_proof_exchange_id = verifier_proof_exchange["proof_id"]
    holder_proof_exchange_id = payload["proof_id"]

    available_credentials = (
        await holder_client.get(
            f"/generic/verifier/proofs/{holder_proof_exchange_id}/credentials",
        )
    ).json()

    cred_id = available_credentials[0]["cred_info"]["referent"]

    verifier_tenant_proofs_listener = SseListener(
        topic="proofs", wallet_id=acme_verifier.tenant_id
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

    event = await verifier_tenant_proofs_listener.wait_for_event(
        field="proof_id",
        field_id=verifier_proof_exchange_id,
        desired_state="done",
    )
    assert event["verified"]
