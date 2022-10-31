from httpx import AsyncClient
import pytest
from app.facades.trust_registry import actor_by_id
from app.tests.util.client import (
    tenant_client,
    tenant_admin_client,
)
from app.tests.util.string import base64_to_json, get_random_string
from app.tests.util.tenants import (
    create_issuer_tenant,
    create_tenant,
    create_verifier_tenant,
    delete_tenant,
)
from app.webhook_listener import start_listener


@pytest.mark.asyncio
async def test_accept_proof_request_verifier_no_public_did(
    governance_client: AsyncClient,
):
    tenant_admin = tenant_admin_client()

    # Create tenants
    verifier_tenant = await create_verifier_tenant(tenant_admin, "acme")
    issuer_tenant = await create_issuer_tenant(tenant_admin, "this-is-it")
    holder_tenant = await create_tenant(tenant_admin, "alice")

    # Get clients
    verifier_client = tenant_client(token=verifier_tenant["access_token"])
    issuer_client = tenant_client(token=issuer_tenant["access_token"])
    holder_client = tenant_client(token=holder_tenant["access_token"])

    # Create connection between issuer and holder
    invitation = (
        await issuer_client.post("/generic/connections/create-invitation")
    ).json()

    wait_for_event, _ = await start_listener(
        topic="connections", wallet_id=issuer_tenant["tenant_id"]
    )
    invitation_response = (
        await holder_client.post(
            "/generic/connections/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    issuer_holder_connection_id = invitation["connection_id"]
    holder_issuer_connection_id = invitation_response["connection_id"]

    await wait_for_event(
        filter_map={"state": "completed", "connection_id": issuer_holder_connection_id}
    )

    # Create connection between holder and verifier
    ## We need to use the multi-use didcomm invitation from the trust registry
    verifier_actor = await actor_by_id(verifier_tenant["tenant_id"])

    assert verifier_actor

    wait_for_event, _ = await start_listener(
        topic="connections",
        wallet_id=verifier_tenant["tenant_id"],
    )

    assert verifier_actor["didcomm_invitation"]

    invitation_json = base64_to_json(
        verifier_actor["didcomm_invitation"].split("?oob=")[1]
    )
    invitation_response = (
        await holder_client.post(
            "/generic/connections/oob/accept-invitation",
            json={"invitation": invitation_json},
        )
    ).json()

    payload = await wait_for_event(filter_map={"state": "completed"}, timeout=100)

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
    credential_definition = (
        await issuer_client.post(
            "/generic/definitions/credentials",
            json={
                "tag": get_random_string(5),
                "schema_id": schema_id,
                "support_revocation": True,
            },
        )
    ).json()

    credential_definition_id = credential_definition["id"]

    # Issue credential from issuer to holder
    wait_for_event, _ = await start_listener(
        topic="credentials", wallet_id=holder_tenant["tenant_id"]
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

    payload = await wait_for_event(
        filter_map={
            "state": "offer-received",
            "connection_id": holder_issuer_connection_id,
        },
    )

    issuer_credential_exchange_id = issuer_credential_exchange["credential_id"]
    holder_credential_exchange_id = payload["credential_id"]

    wait_for_event, _ = await start_listener(
        topic="credentials", wallet_id=issuer_tenant["tenant_id"]
    )

    response = await holder_client.post(
        f"/generic/issuer/credentials/{holder_credential_exchange_id}/request"
    )
    response.raise_for_status()

    # Wait for credential exchange to finish
    await wait_for_event(
        filter_map={"state": "done", "credential_id": issuer_credential_exchange_id},
        timeout=300,
    )

    # Present proof from holder to verifier

    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=holder_tenant["tenant_id"]
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

    response.raise_for_status()
    verifier_proof_exchange = response.json()

    payload = await wait_for_event(
        filter_map={
            "state": "request-received",
            "connection_id": holder_verifier_connection_id,
        },
        timeout=300,
    )

    verifier_proof_exchange_id = verifier_proof_exchange["proof_id"]
    holder_proof_exchange_id = payload["proof_id"]

    available_credentials = (
        await holder_client.get(
            f"/generic/verifier/proofs/{holder_proof_exchange_id}/credentials",
        )
    ).json()

    cred_id = available_credentials[0]["cred_info"]["referent"]

    wait_for_event, _ = await start_listener(
        topic="proofs", wallet_id=verifier_tenant["tenant_id"]
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
    response.raise_for_status()

    await wait_for_event(
        filter_map={
            "state": "done",
            "proof_id": verifier_proof_exchange_id,
            "verified": True,
        },
        timeout=300,
    )

    # Delete all tenants
    await delete_tenant(tenant_admin, issuer_tenant["tenant_id"])
    await delete_tenant(tenant_admin, verifier_tenant["tenant_id"])
    await delete_tenant(tenant_admin, holder_tenant["tenant_id"])
