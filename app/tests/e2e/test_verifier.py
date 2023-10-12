import time

import pytest
from aries_cloudcontroller import (
    AttachmentDef,
    IndyPresSpec,
    IndyRequestedCredsRequestedAttr,
)
from assertpy import assert_that

from app.event_handling.sse_listener import SseListener
from app.models.tenants import CreateTenantResponse
from app.routes.oob import AcceptOobInvitation, CreateOobInvitation
from app.routes.oob import router as oob_router
from app.routes.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
    SendProofRequest,
    router,
)
from app.tests.util.ecosystem_connections import AcmeAliceConnect
from app.tests.util.webhooks import check_webhook_state, get_wallet_id_from_async_client
from app.tests.verifier.utils import indy_proof_request
from shared import RichAsyncClient
from shared.models.protocol import PresentProofProtocolVersion
from shared.models.topics import CredentialExchange, PresentationExchange

VERIFIER_BASE_PATH = router.prefix
OOB_BASE_PATH = oob_router.prefix


def create_send_request(
    connection_id: str, protocol_version: PresentProofProtocolVersion
) -> SendProofRequest:
    return SendProofRequest(
        protocol_version=protocol_version.value,
        connection_id=connection_id,
        indy_proof_request=indy_proof_request,
    )


@pytest.mark.anyio
async def test_accept_proof_request_v1(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: RichAsyncClient,
    acme_client: RichAsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
):
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )
    acme_exchange = response.json()
    acme_proof_id = acme_exchange["proof_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-received"},
        topic="proofs",
        max_duration=240,
    )
    proof_records_alice = await alice_member_client.get(VERIFIER_BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-received", "proof_id": alice_proof_id},
        topic="proofs",
        max_duration=120,
    )

    referent = requested_credentials.json()[-1]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )

    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        indy_presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "done", "proof_id": alice_proof_id},
        topic="proofs",
        max_duration=240,
    )

    assert await check_webhook_state(
        client=acme_client,
        filter_map={"state": "done", "proof_id": acme_proof_id},
        topic="proofs",
        max_duration=240,
    )

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_accept_proof_request_oob_v1(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
):
    alice_tenant_id = get_wallet_id_from_async_client(alice_member_client)
    bob_tenant_id = get_wallet_id_from_async_client(bob_member_client)

    alice_proofs_listener = SseListener(topic="proofs", wallet_id=alice_tenant_id)
    bob_proofs_listener = SseListener(topic="proofs", wallet_id=bob_tenant_id)

    # Create the proof request against aca-py
    create_proof_request = CreateProofRequest(
        indy_proof_request=indy_proof_request,
        auto_verify=True,
        comment="some comment",
        protocol_version=PresentProofProtocolVersion.v1.value,
    )

    create_proof_response = await bob_member_client.post(
        VERIFIER_BASE_PATH + "/create-request", json=create_proof_request.model_dump()
    )
    bob_exchange = create_proof_response.json()
    thread_id = bob_exchange["thread_id"]

    create_oob_invitation_request = CreateOobInvitation(
        create_connection=False,
        use_public_did=False,
        attachments=[AttachmentDef(id=bob_exchange["proof_id"], type="present-proof")],
    )

    invitation_response = await bob_member_client.post(
        f"{OOB_BASE_PATH}/create-invitation",
        json=create_oob_invitation_request.model_dump(),
    )
    assert invitation_response.status_code == 200
    invitation = (invitation_response.json())["invitation"]

    accept_oob_invitation_request = AcceptOobInvitation(invitation=invitation)
    await alice_member_client.post(
        f"{OOB_BASE_PATH}/accept-invitation",
        json=accept_oob_invitation_request.model_dump(by_alias=True),
    )

    alice_request_received = await alice_proofs_listener.wait_for_event(
        field="thread_id",
        field_id=thread_id,
        desired_state="request-received",
    )

    alice_proof_id = alice_request_received["proof_id"]
    assert alice_proof_id

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    referent = requested_credentials.json()[0]["cred_info"]["referent"]
    assert referent

    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        indy_presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    accept_response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )
    assert accept_response.status_code == 200

    alice_presentation_sent = await alice_proofs_listener.wait_for_event(
        field="proof_id",
        field_id=alice_proof_id,
        desired_state="presentation-sent",
    )
    assert alice_presentation_sent

    bob_presentation_received = await bob_proofs_listener.wait_for_event(
        field="thread_id",
        field_id=thread_id,
        desired_state="done",
    )
    assert bob_presentation_received["role"] == "verifier"


@pytest.mark.anyio
async def test_accept_proof_request_oob_v2(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
):
    alice_tenant_id = get_wallet_id_from_async_client(alice_member_client)
    bob_tenant_id = get_wallet_id_from_async_client(bob_member_client)

    alice_proofs_listener = SseListener(topic="proofs", wallet_id=alice_tenant_id)
    bob_proofs_listener = SseListener(topic="proofs", wallet_id=bob_tenant_id)

    # Create the proof request against aca-py
    response = await bob_member_client.post(
        VERIFIER_BASE_PATH + "/create-request",
        json={
            "comment": "some comment",
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )
    bob_exchange = response.json()

    thread_id = bob_exchange["thread_id"]

    invitation_response = await bob_member_client.post(
        f"{OOB_BASE_PATH}/create-invitation",
        json={
            "create_connection": False,
            "use_public_did": False,
            "attachments": [{"id": bob_exchange["proof_id"], "type": "present-proof"}],
        },
    )

    assert_that(invitation_response.status_code).is_equal_to(200)
    invitation = (invitation_response.json())["invitation"]

    await alice_member_client.post(
        f"{OOB_BASE_PATH}/accept-invitation",
        json={"invitation": invitation},
    )

    alice_request_received = await alice_proofs_listener.wait_for_event(
        field="thread_id",
        field_id=thread_id,
        desired_state="request-received",
    )

    alice_proof_id = alice_request_received["proof_id"]
    assert alice_proof_id

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    referent = requested_credentials.json()[0]["cred_info"]["referent"]
    assert referent

    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        indy_presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )

    alice_presentation_sent = await alice_proofs_listener.wait_for_event(
        field="proof_id",
        field_id=alice_proof_id,
        desired_state="presentation-sent",
    )
    assert alice_presentation_sent

    bob_presentation_received = await bob_proofs_listener.wait_for_event(
        field="thread_id",
        field_id=thread_id,
        desired_state="done",
    )
    assert bob_presentation_received["role"] == "verifier"


@pytest.mark.anyio
async def test_accept_proof_request_v2(
    issue_credential_to_alice: CredentialExchange,
    alice_member_client: RichAsyncClient,
    acme_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    acme_verifier: CreateTenantResponse,
    credential_definition_id: str,
    acme_and_alice_connection: AcmeAliceConnect,
):
    alice_proofs_listener = SseListener(
        topic="proofs", wallet_id=alice_tenant.tenant_id
    )

    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            # Custom proof request because v2 doesn't support proof request without restrictions
            # see: https://github.com/hyperledger/aries-cloudagent-python/issues/1755
            "indy_proof_request": {
                "name": "Proof Request",
                "version": "1.0.0",
                "requested_attributes": {
                    "0_speed_uuid": {
                        "name": "speed",
                        "restrictions": [{"cred_def_id": credential_definition_id}],
                    }
                },
                "requested_predicates": {},
            },
        },
    )
    acme_exchange = response.json()
    acme_proof_id = acme_exchange["proof_id"]

    payload = await alice_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=acme_and_alice_connection.alice_connection_id,
        desired_state="request-received",
    )

    alice_proof_id = payload["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    referent = requested_credentials.json()[-1]["cred_info"]["referent"]
    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )
    proof_accept = AcceptProofRequest(
        proof_id=alice_proof_id,
        indy_presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    acme_proofs_listener = SseListener(
        topic="proofs", wallet_id=acme_verifier.tenant_id
    )

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )

    acme_proof_event = await acme_proofs_listener.wait_for_event(
        field="proof_id",
        field_id=acme_proof_id,
        desired_state="done",
    )
    assert acme_proof_event["verified"]

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_send_proof_request(
    acme_and_alice_connection: AcmeAliceConnect,
    acme_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
):
    alice_proofs_listener = SseListener(
        topic="proofs", wallet_id=alice_tenant.tenant_id
    )
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    result = response.json()

    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert result["role"] == "verifier"
    assert result["state"]

    time.sleep(0.5)
    # Allow webhook event to be registered in SSE before querying. Only necessary because
    # we are querying by connection_id, and will return previous result if we don't add short wait
    alice_connection_event = await alice_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=acme_and_alice_connection.alice_connection_id,
        desired_state="request-received",
    )
    assert alice_connection_event["protocol_version"] == "v1"

    # V2
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v2-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]

    time.sleep(0.5)
    # Allow webhook event to be registered in SSE before querying. Only necessary because
    # we are querying by connection_id, and will return previous result if we don't add short wait

    alice_connection_event = await alice_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=acme_and_alice_connection.alice_connection_id,
        desired_state="request-received",
    )
    assert alice_connection_event["protocol_version"] == "v2"


@pytest.mark.anyio
async def test_reject_proof_request(
    acme_and_alice_connection: AcmeAliceConnect,
    alice_member_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    acme_client: RichAsyncClient,
):
    alice_proofs_listener = SseListener(
        topic="proofs", wallet_id=alice_tenant.tenant_id
    )

    # V1
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    time.sleep(0.5)
    # Allow webhook event to be registered in SSE before querying. Only necessary because
    # we are querying by connection_id, and will return previous result if we don't add short wait

    alice_exchange = await alice_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=acme_and_alice_connection.alice_connection_id,
        desired_state="request-received",
    )
    assert alice_exchange["protocol_version"] == "v1"

    reject_proof_request_v1 = RejectProofRequest(
        proof_id=alice_exchange["proof_id"], problem_report=None
    )

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/reject-request",
        json=reject_proof_request_v1.model_dump(),
    )
    assert response.status_code == 204


@pytest.mark.anyio
async def test_get_proof_single(
    acme_and_alice_connection: AcmeAliceConnect, acme_client: RichAsyncClient
):
    # V1
    proof_req_res = await acme_client.post(
        f"{VERIFIER_BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    proof_id = proof_req_res.json()["proof_id"]
    response = await acme_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{proof_id}",
    )
    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "presentation_request" in result

    # V2
    proof_req_res = await acme_client.post(
        f"{VERIFIER_BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    proof_id = proof_req_res.json()["proof_id"]

    response = await acme_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{proof_id}",
    )

    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v2-" in result["proof_id"]
    assert "presentation_request" in result


@pytest.mark.anyio
async def test_get_proofs_multi(
    acme_and_alice_connection: AcmeAliceConnect, acme_client: RichAsyncClient
):
    # V1
    await acme_client.post(
        f"{VERIFIER_BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    response = await acme_client.get(
        f"{VERIFIER_BASE_PATH}/proofs",
    )

    result = response.json()[0]
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v1-" in result["proof_id"]
    assert "presentation_request" in result

    # V2
    await acme_client.post(
        f"{VERIFIER_BASE_PATH}/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    response = await acme_client.get(
        VERIFIER_BASE_PATH + "/proofs",
    )

    result = response.json()[-1]
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v2-" in result["proof_id"]
    assert "presentation_request" in result


@pytest.mark.anyio
async def test_delete_proof(
    acme_and_alice_connection: AcmeAliceConnect, acme_client: RichAsyncClient
):
    # V1
    proof_req_res = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await acme_client.delete(
        VERIFIER_BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.status_code == 204

    # V2
    proof_req_res = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await acme_client.delete(
        f"{VERIFIER_BASE_PATH}/proofs/{proof_id}",
    )
    assert response.status_code == 204


@pytest.mark.anyio
async def test_get_credentials_for_request(
    issue_credential_to_alice: CredentialExchange,
    acme_and_alice_connection: AcmeAliceConnect,
    acme_client: RichAsyncClient,
    alice_tenant: CreateTenantResponse,
    alice_member_client: RichAsyncClient,
):
    alice_proofs_listener = SseListener(
        topic="proofs", wallet_id=alice_tenant.tenant_id
    )
    # V1
    await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    time.sleep(0.5)
    # Allow webhook event to be registered in SSE before querying. Only necessary because
    # we are querying by connection_id, and will return previous result if we don't add short wait

    alice_exchange = await alice_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=acme_and_alice_connection.alice_connection_id,
        desired_state="request-received",
    )
    assert alice_exchange["protocol_version"] == "v1"

    proof_id = alice_exchange["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{proof_id}/credentials",
    )

    result = requested_credentials.json()[-1]
    assert "cred_info" in result.keys()
    assert [
        attr
        in ["attrs", "cred_def_info", "referent", "interval", "presentation_referents"]
        for attr in result["cred_info"].keys()
    ]

    # V2
    await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.model_dump(),
        },
    )

    time.sleep(0.5)
    # Allow webhook event to be registered in SSE before querying. Only necessary because
    # we are querying by connection_id, and will return previous result if we don't add short wait

    alice_exchange = await alice_proofs_listener.wait_for_event(
        field="connection_id",
        field_id=acme_and_alice_connection.alice_connection_id,
        desired_state="request-received",
    )
    assert alice_exchange["protocol_version"] == "v2"

    proof_id = alice_exchange["proof_id"]

    response = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{proof_id}/credentials",
    )

    result = response.json()[-1]
    assert "cred_info" in result.keys()
    assert [
        attr
        in ["attrs", "cred_def_info", "referent", "interval", "presentation_referents"]
        for attr in result["cred_info"].keys()
    ]
