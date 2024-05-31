import pytest
from aries_cloudcontroller import IndyPresSpec
from fastapi import HTTPException

from app.routes.verifier import AcceptProofRequest, router
from app.tests.util.connections import AcmeAliceConnect
from app.tests.util.verifier import send_proof_request
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient
from shared.models.credential_exchange import CredentialExchange
from shared.models.presentation_exchange import PresentationExchange

VERIFIER_BASE_PATH = router.prefix


@pytest.mark.anyio
@pytest.mark.parametrize("protocol_version", ["v1", "v2"])
@pytest.mark.parametrize("predicate", ["<", ">", "<=", ">="])
async def test_predicate_proofs(
    protocol_version: str,
    acme_client: RichAsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
    alice_member_client: RichAsyncClient,
    issue_credential_to_alice: CredentialExchange,  # pylint: disable=unused-argument
    predicate: str,
):
    request_body = {
        "type": "indy",
        "protocol_version": protocol_version,
        "indy_proof_request": {
            "requested_attributes": {},
            "requested_predicates": {
                "over_18": {
                    "name": "age",
                    "p_type": predicate,
                    "p_value": 18,
                }
            },
        },
        "connection_id": acme_and_alice_connection.acme_connection_id,
        "save_exchange_record": True,
    }

    send_proof_response = await send_proof_request(acme_client, request_body)

    thread_id = send_proof_response["thread_id"]

    alice_event = await check_webhook_state(
        client=alice_member_client,
        topic="proofs",
        filter_map={"thread_id": thread_id},
        state="request-received",
    )
