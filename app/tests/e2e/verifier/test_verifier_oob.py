import pytest
from aries_cloudcontroller import (
    AttachmentDef,
    IndyPresSpec,
    IndyRequestedCredsRequestedAttr,
)

from app.routes.oob import AcceptOobInvitation, CreateOobInvitation
from app.routes.oob import router as oob_router
from app.routes.verifier import AcceptProofRequest, CreateProofRequest
from app.routes.verifier import router as verifier_router
from app.tests.services.verifier.utils import indy_proof_request
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange

OOB_BASE_PATH = oob_router.prefix
VERIFIER_BASE_PATH = verifier_router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
async def test_accept_proof_request_oob(
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    alice_member_client: RichAsyncClient,
    bob_member_client: RichAsyncClient,
    protocol_version: str,
):
    # Create the proof request against aca-py
    create_proof_request = CreateProofRequest(
        indy_proof_request=indy_proof_request,
        comment="some comment",
        protocol_version=protocol_version,
    )
    create_proof_response = await bob_member_client.post(
        VERIFIER_BASE_PATH + "/create-request",
        json=create_proof_request.model_dump(by_alias=True),
    )
    bob_exchange = create_proof_response.json()
    assert bob_exchange["protocol_version"] == protocol_version
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
