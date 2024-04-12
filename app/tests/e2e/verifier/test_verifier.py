import json

import pytest
from aries_cloudcontroller import (
    AttachmentDef,
    IndyPresSpec,
    IndyRequestedCredsRequestedAttr,
)
from assertpy import assert_that
from fastapi import HTTPException

from app.routes.connections import router as conn_router
from app.routes.definitions import router as def_router
from app.routes.issuer import router as issuer_router
from app.routes.oob import AcceptOobInvitation, CreateOobInvitation
from app.routes.oob import router as oob_router
from app.routes.verifier import (
    AcceptProofRequest,
    CreateProofRequest,
    RejectProofRequest,
)
from app.routes.verifier import router as verifier_router
from app.services.trust_registry.actors import fetch_actor_by_id
from app.tests.services.verifier.utils import indy_proof_request
from app.tests.util.ecosystem_connections import AcmeAliceConnect, MeldCoAliceConnect
from app.tests.util.webhooks import check_webhook_state, get_wallet_id_from_async_client
from app.util.string import base64_to_json, random_string
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange
from shared.models.presentation_exchange import PresentationExchange
from shared.models.protocol import PresentProofProtocolVersion

CONNECTIONS_BASE_PATH = conn_router.prefix
DEFINITIONS_BASE_PATH = def_router.prefix
ISSUER_BASE_PATH = issuer_router.prefix
OOB_BASE_PATH = oob_router.prefix
VERIFIER_BASE_PATH = verifier_router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize(
    "acme_and_alice_connection", ["trust_registry", "default"], indirect=True
)
async def test_accept_proof_request_v1(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    acme_client: RichAsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
):
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )
    acme_exchange = response.json()
    acme_proof_id = acme_exchange["proof_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
    )
    proof_records_alice = await alice_member_client.get(VERIFIER_BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "proof_id": alice_proof_id,
        },
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
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": alice_proof_id,
        },
        look_back=5,
    )

    assert await check_webhook_state(
        client=acme_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": acme_proof_id,
        },
        look_back=5,
    )

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.anyio
async def test_accept_proof_request_oob_v1(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
):
    # Create the proof request against aca-py
    create_proof_request = CreateProofRequest(
        indy_proof_request=indy_proof_request,
        comment="some comment",
        protocol_version=PresentProofProtocolVersion.v1.value,
    )

    create_proof_response = await bob_member_client.post(
        VERIFIER_BASE_PATH + "/create-request",
        json=create_proof_request.model_dump(by_alias=True),
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

    alice_request_received = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
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

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="presentation-sent",
        filter_map={
            "proof_id": alice_proof_id,
        },
    )

    bob_presentation_received = await check_webhook_state(
        client=bob_member_client,
        topic="proofs",
        state="done",
        filter_map={
            "thread_id": thread_id,
        },
    )
    assert bob_presentation_received["role"] == "verifier"


@pytest.mark.anyio
async def test_accept_proof_request_oob_v2(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
):
    # Create the proof request against aca-py
    response = await bob_member_client.post(
        VERIFIER_BASE_PATH + "/create-request",
        json={
            "comment": "some comment",
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.to_dict(),
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

    alice_request_received = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
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

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="presentation-sent",
        filter_map={
            "proof_id": alice_proof_id,
        },
    )

    bob_presentation_received = await check_webhook_state(
        client=bob_member_client,
        topic="proofs",
        state="done",
        filter_map={
            "thread_id": thread_id,
        },
    )
    assert bob_presentation_received["role"] == "verifier"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "acme_and_alice_connection", ["trust_registry", "default"], indirect=True
)
async def test_accept_proof_request_v2(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    acme_client: RichAsyncClient,
    credential_definition_id: str,
    acme_and_alice_connection: AcmeAliceConnect,
):
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

    payload = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "connection_id": acme_and_alice_connection.alice_connection_id,
        },
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

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )

    acme_proof_event = await check_webhook_state(
        client=acme_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": acme_proof_id,
        },
    )
    assert acme_proof_event["verified"]

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize(
    "acme_and_alice_connection", ["trust_registry", "default"], indirect=True
)
async def test_send_proof_request(
    acme_and_alice_connection: AcmeAliceConnect,
    acme_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    result = response.json()

    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert result["role"] == "verifier"
    assert result["state"]

    thread_id = result["thread_id"]
    assert thread_id

    alice_connection_event = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
    )
    assert alice_connection_event["protocol_version"] == "v1"

    # V2
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.to_dict(),
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

    thread_id = result["thread_id"]
    assert thread_id

    alice_connection_event = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
    )
    assert alice_connection_event["protocol_version"] == "v2"


@pytest.mark.anyio
async def test_reject_proof_request(
    acme_and_alice_connection: AcmeAliceConnect,
    alice_member_client: RichAsyncClient,
    acme_client: RichAsyncClient,
):
    # V1
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    thread_id = response.json()["thread_id"]
    assert thread_id

    alice_exchange = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
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
            "indy_proof_request": indy_proof_request.to_dict(),
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
            "indy_proof_request": indy_proof_request.to_dict(),
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
            "indy_proof_request": indy_proof_request.to_dict(),
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
            "indy_proof_request": indy_proof_request.to_dict(),
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
            "indy_proof_request": indy_proof_request.to_dict(),
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
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await acme_client.delete(
        f"{VERIFIER_BASE_PATH}/proofs/{proof_id}",
    )
    assert response.status_code == 204


@pytest.mark.anyio
async def test_get_credentials_for_request(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    acme_and_alice_connection: AcmeAliceConnect,
    acme_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    # V1
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    thread_id = response.json()["thread_id"]
    assert thread_id

    alice_exchange = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
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
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    thread_id = response.json()["thread_id"]
    assert thread_id

    alice_exchange = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
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


@pytest.mark.anyio
@pytest.mark.parametrize(
    "meld_co_and_alice_connection", ["trust_registry", "default"], indirect=True
)
async def test_accept_proof_request_v1_verifier_has_issuer_role(
    meld_co_issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    meld_co_client: RichAsyncClient,
    meld_co_and_alice_connection: MeldCoAliceConnect,
):
    response = await meld_co_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": meld_co_and_alice_connection.meld_co_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )
    meld_co_exchange = response.json()
    meld_co_proof_id = meld_co_exchange["proof_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
    )
    proof_records_alice = await alice_member_client.get(VERIFIER_BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "proof_id": alice_proof_id,
        },
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
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": alice_proof_id,
        },
        look_back=5,
    )

    assert await check_webhook_state(
        client=meld_co_client,
        state="done",
        filter_map={
            "proof_id": meld_co_proof_id,
        },
        topic="proofs",
        look_back=5,
    )

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.parametrize(
    "meld_co_and_alice_connection", ["trust_registry", "default"], indirect=True
)
async def test_send_proof_request_verifier_has_issuer_role(
    meld_co_and_alice_connection: MeldCoAliceConnect,
    meld_co_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    response = await meld_co_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": meld_co_and_alice_connection.meld_co_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    result = response.json()

    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert result["role"] == "verifier"
    assert result["state"]

    thread_id = result["thread_id"]
    assert thread_id

    alice_connection_event = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
    )
    assert alice_connection_event["protocol_version"] == "v1"

    # V2
    response = await meld_co_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": meld_co_and_alice_connection.meld_co_connection_id,
            "protocol_version": "v2",
            "indy_proof_request": indy_proof_request.to_dict(),
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

    thread_id = result["thread_id"]
    assert thread_id

    alice_connection_event = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "thread_id": thread_id,
        },
    )
    assert alice_connection_event["protocol_version"] == "v2"


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
@pytest.mark.parametrize("acme_save_exchange_record", [False, True])
@pytest.mark.parametrize("alice_save_exchange_record", [False, True])
async def test_saving_of_presentation_exchange_records(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    acme_client: RichAsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
    protocol_version: str,
    acme_save_exchange_record: bool,
    alice_save_exchange_record: bool,
):
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "connection_id": acme_and_alice_connection.acme_connection_id,
            "protocol_version": protocol_version,
            "indy_proof_request": indy_proof_request.to_dict(),
            "save_exchange_record": acme_save_exchange_record,
        },
    )
    acme_exchange = response.json()
    acme_proof_id = acme_exchange["proof_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
    )
    proof_records_alice = await alice_member_client.get(VERIFIER_BASE_PATH + "/proofs")
    alice_proof_id = proof_records_alice.json()[-1]["proof_id"]

    requested_credentials = await alice_member_client.get(
        f"{VERIFIER_BASE_PATH}/proofs/{alice_proof_id}/credentials"
    )

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "proof_id": alice_proof_id,
        },
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
        save_exchange_record=alice_save_exchange_record,
    )

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )

    assert await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": alice_proof_id,
        },
        look_back=5,
    )

    assert await check_webhook_state(
        client=acme_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": acme_proof_id,
        },
        look_back=5,
    )

    result = response.json()

    pres_exchange_result = PresentationExchange(**result)
    assert isinstance(pres_exchange_result, PresentationExchange)
    assert response.status_code == 200

    # After proof request is complete, get exchange records from faber side:
    acme_pres_ex_records = (
        await acme_client.get(f"{VERIFIER_BASE_PATH}/proofs")
    ).json()

    # get exchange records from alice side
    alice_pres_ex_records = (
        await alice_member_client.get(f"{VERIFIER_BASE_PATH}/proofs")
    ).json()

    if alice_save_exchange_record:
        assert (
            len(alice_pres_ex_records) == 1
        )  # Save record is True, should be 1 record
    else:
        assert len(alice_pres_ex_records) == 0  # default is to remove records

    if acme_save_exchange_record:
        assert len(acme_pres_ex_records) == 1  # Save record is True, should be 1 record
    else:
        assert len(acme_pres_ex_records) == 0  # default is to remove records


@pytest.mark.anyio
async def test_accept_proof_request_verifier_no_public_did(
    governance_client: RichAsyncClient,
    acme_client: RichAsyncClient,
    faber_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
):
    # Create connection between issuer and holder
    invitation = (
        await faber_client.post(CONNECTIONS_BASE_PATH + "/create-invitation")
    ).json()

    invitation_response = (
        await alice_member_client.post(
            CONNECTIONS_BASE_PATH + "/accept-invitation",
            json={"invitation": invitation["invitation"]},
        )
    ).json()

    issuer_holder_connection_id = invitation["connection_id"]
    holder_issuer_connection_id = invitation_response["connection_id"]

    await check_webhook_state(
        client=faber_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": issuer_holder_connection_id,
        },
    )

    # Create connection between holder and verifier
    # We need to use the multi-use didcomm invitation from the trust registry
    acme_wallet_id = get_wallet_id_from_async_client(acme_client)
    verifier_actor = await fetch_actor_by_id(acme_wallet_id)

    assert verifier_actor
    assert verifier_actor["didcomm_invitation"]

    invitation_json = base64_to_json(
        verifier_actor["didcomm_invitation"].split("?oob=")[1]
    )
    invitation_response = (
        await alice_member_client.post(
            OOB_BASE_PATH + "/accept-invitation",
            json={"invitation": invitation_json},
        )
    ).json()

    payload = await check_webhook_state(
        client=acme_client,
        topic="connections",
        state="completed",
    )
    holder_verifier_connection_id = invitation_response["connection_id"]
    verifier_holder_connection_id = payload["connection_id"]

    # Create schema as governance
    schema = (
        await governance_client.post(
            DEFINITIONS_BASE_PATH + "/schemas",
            json={
                "name": "e2e-flow",
                "version": "1.0.0",
                "attribute_names": ["name", "age"],
            },
        )
    ).json()

    schema_id = schema["id"]

    # Create credential definition as issuer
    credential_definition = await faber_client.post(
        DEFINITIONS_BASE_PATH + "/credentials",
        json={
            "tag": random_string(5),
            "schema_id": schema_id,
        },
    )

    if credential_definition.is_client_error:
        raise Exception(credential_definition.json()["detail"])

    credential_definition_id = credential_definition.json()["id"]

    # Issue credential from issuer to holder
    issuer_credential_exchange = (
        await faber_client.post(
            f"{ISSUER_BASE_PATH}",
            json={
                "protocol_version": "v1",
                "connection_id": issuer_holder_connection_id,
                "indy_credential_detail": {
                    "credential_definition_id": credential_definition_id,
                    "attributes": {"name": "Alice", "age": "44"},
                },
            },
        )
    ).json()

    payload = await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        filter_map={
            "connection_id": holder_issuer_connection_id,
        },
    )

    issuer_credential_exchange_id = issuer_credential_exchange["credential_id"]
    holder_credential_exchange_id = payload["credential_id"]

    response = await alice_member_client.post(
        f"{ISSUER_BASE_PATH}/{holder_credential_exchange_id}/request"
    )

    # Wait for credential exchange to finish
    await check_webhook_state(
        client=faber_client,
        topic="credentials",
        state="done",
        filter_map={
            "credential_id": issuer_credential_exchange_id,
        },
    )

    # Present proof from holder to verifier
    response = await acme_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "protocol_version": "v1",
            "connection_id": verifier_holder_connection_id,
            "indy_proof_request": {
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
                        "p_value": 21,
                        "restrictions": [{"cred_def_id": credential_definition_id}],
                    }
                },
            },
        },
    )

    verifier_proof_exchange = response.json()

    payload = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
        filter_map={
            "connection_id": holder_verifier_connection_id,
        },
    )

    verifier_proof_exchange_id = verifier_proof_exchange["proof_id"]
    holder_proof_exchange_id = payload["proof_id"]

    available_credentials = (
        await alice_member_client.get(
            f"{VERIFIER_BASE_PATH}/proofs/{holder_proof_exchange_id}/credentials",
        )
    ).json()

    cred_id = available_credentials[0]["cred_info"]["referent"]

    response = await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json={
            "proof_id": holder_proof_exchange_id,
            "indy_presentation_spec": {
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

    event = await check_webhook_state(
        client=acme_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": verifier_proof_exchange_id,
        },
    )
    assert event["verified"]


@pytest.mark.anyio
async def test_get_proof_records(
    meld_co_client: RichAsyncClient,
    meld_co_and_alice_connection: MeldCoAliceConnect,
    meld_co_issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
):
    meld_connection_id = meld_co_and_alice_connection.meld_co_connection_id

    # Meld_co does proof request and alice responds
    proof = await meld_co_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "save_exchange_record": True,
            "connection_id": meld_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )

    proof_1 = proof.json()
    assert proof.status_code == 200
    assert proof_1["state"] == "request-sent"

    await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="request-received",
    )

    proof_exc = await alice_member_client.get(f"{VERIFIER_BASE_PATH}/proofs")
    assert proof_exc.status_code == 200

    proof_request = proof_exc.json()[0]

    referent = (
        await alice_member_client.get(
            f"{VERIFIER_BASE_PATH}/proofs/{proof_request['proof_id']}/credentials"
        )
    ).json()[0]["cred_info"]["referent"]

    indy_request_attrs = IndyRequestedCredsRequestedAttr(
        cred_id=referent, revealed=True
    )

    proof_accept = AcceptProofRequest(
        proof_id=proof_exc.json()[0]["proof_id"],
        indy_presentation_spec=IndyPresSpec(
            requested_attributes={"0_speed_uuid": indy_request_attrs},
            requested_predicates={},
            self_attested_attributes={},
        ),
    )

    await alice_member_client.post(
        VERIFIER_BASE_PATH + "/accept-request",
        json=proof_accept.model_dump(),
    )

    await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": proof_request["proof_id"],
        },
    )
    await check_webhook_state(
        client=meld_co_client,
        topic="proofs",
        state="done",
        filter_map={
            "proof_id": proof_1["proof_id"],
        },
    )

    meld_proof = await meld_co_client.get(f"{VERIFIER_BASE_PATH}/proofs")
    assert meld_proof.status_code == 200
    meld_proof_exchange = meld_proof.json()

    # Make sure the proof is done
    for proof in meld_proof_exchange:
        if proof["proof_id"] == proof_1["proof_id"]:
            assert proof["state"] == "done"

    # Meld_co does proof request and alice does not respond
    proof = await meld_co_client.post(
        VERIFIER_BASE_PATH + "/send-request",
        json={
            "save_exchange_record": True,
            "connection_id": meld_connection_id,
            "protocol_version": "v1",
            "indy_proof_request": indy_proof_request.to_dict(),
        },
    )
    proof_2 = proof.json()
    proofs = await meld_co_client.get(f"{VERIFIER_BASE_PATH}/proofs")

    # Make sure both proofs are in the list
    proof_ids = [proof_1["proof_id"], proof_2["proof_id"]]
    proof_count = sum(1 for proof in proofs.json() if proof["proof_id"] in proof_ids)
    assert proof_count == 2

    # Now test query params
    proofs_sent = await meld_co_client.get(
        f"{VERIFIER_BASE_PATH}/proofs?state=request-sent"
    )
    assert proofs.status_code == 200
    for proof in proofs_sent.json():
        assert proof["state"] == "request-sent"

    proofs_done = await meld_co_client.get(f"{VERIFIER_BASE_PATH}/proofs?state=done")
    assert proofs.status_code == 200
    for proof in proofs_done.json():
        assert proof["state"] == "done"

    proofs_role = await meld_co_client.get(f"{VERIFIER_BASE_PATH}/proofs?role=verifier")
    assert proofs.status_code == 200
    for proof in proofs_role.json():
        assert proof["role"] == "verifier"

    proofs_prover = await meld_co_client.get(f"{VERIFIER_BASE_PATH}/proofs?role=prover")
    assert proofs.status_code == 200
    assert len(proofs_prover.json()) == 0

    proofs = await meld_co_client.get(
        f"{VERIFIER_BASE_PATH}/proofs?connection_id={meld_connection_id}&state=done"
    )
    assert proofs.status_code == 200
    assert len(proofs.json()) == 1

    proofs = await meld_co_client.get(
        f"{VERIFIER_BASE_PATH}/proofs?connection_id={meld_connection_id}&state=request-sent"
    )
    assert proofs.status_code == 200
    assert len(proofs.json()) == 1

    proofs = await meld_co_client.get(
        f"{VERIFIER_BASE_PATH}/proofs?connection_id={meld_connection_id}&thread_id={proof_1['thread_id']}"
    )
    assert proofs.status_code == 200
    assert len(proofs.json()) == 1

    proofs = await meld_co_client.get(
        f"{VERIFIER_BASE_PATH}/proofs?connection_id={meld_connection_id}&thread_id={proof_2['thread_id']}"
    )
    assert proofs.status_code == 200
    assert len(proofs.json()) == 1

    with pytest.raises(HTTPException) as exc:
        await meld_co_client.get(
            f"{VERIFIER_BASE_PATH}/proofs?connection_id=123&state=invalid&role=invalid&thread_id=invalid"
        )
    assert exc.value.status_code == 422
    assert len(json.loads(exc.value.detail)["detail"]) == 3
