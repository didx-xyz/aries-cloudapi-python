<<<<<<< HEAD
import time
import json
from aries_cloudcontroller.model.indy_pres_spec import IndyPresSpec
from aries_cloudcontroller.model.indy_requested_creds_requested_pred import (
    IndyRequestedCredsRequestedPred,
)
=======
>>>>>>> development
import pytest
from aries_cloudcontroller import (
    IndyProofRequest,
    SchemaSendResult,
    IndyRequestedCredsRequestedAttr,
)
from assertpy import assert_that
from httpx import AsyncClient
from app.generic.issuer.models import CredentialExchange

from app.generic.verifier.models import (
    AcceptProofRequest,
    CreateProofRequest,
    ProofRequestProtocolVersion,
    RejectProofRequest,
    SendProofRequest,
)
from app.facades.trust_registry import (
    Actor,
    register_actor,
)
from app.tests.util.event_loop import event_loop
from app.tests.util.webhooks import check_webhook_state
from app.tests.util.member_personas import (
    BobAliceConnect,
    MultiInvite,
)
from app.tests.util.trust_registry import register_verifier
from app.tests.verifier.test_verifier_utils import indy_pres_spec, proof_dict
from app.tests.e2e.test_fixtures import BASE_PATH
from app.tests.e2e.test_fixtures import *  # NOQA

BASE_PATH = "/generic/verifier"


def create_send_request(connection_id: str, protocol_version: str) -> SendProofRequest:
    return SendProofRequest(
        protocol_version=protocol_version,
        connection_id=connection_id,
        proof_request=IndyProofRequest(**proof_dict["proof_request"]),
    )


@pytest.mark.asyncio
async def test_send_proof_request(
    bob_and_alice_connection: BobAliceConnect,
    schema_definition: SchemaSendResult,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        connection_id=bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )

    pred_keys = proof_request_v1.proof_request.requested_predicates.keys()
    attr_keys = proof_request_v1.proof_request.requested_attributes.keys()

    proof_request_v1.proof_request.requested_attributes[
        schema_definition.schema_id
    ] = proof_request_v1.proof_request.requested_attributes.pop(list(attr_keys)[0])

    proof_request_v1.proof_request.requested_predicates[
        schema_definition.schema_id
    ] = proof_request_v1.proof_request.requested_predicates.pop(list(pred_keys)[0])

    await register_verifier(alice_member_client, schema_definition.schema_id)
    response = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )
    # await register_actor(actor=Actor())

    result = response.json()
    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert result["role"] == "verifier"
    assert result["state"]

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value
    response = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "presentation_request" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v2-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]


@pytest.mark.asyncio
async def test_create_proof_request(
    alice_member_client: AsyncClient,
    schema_definition: SchemaSendResult,
):
    # V1
    proof_request_v1 = CreateProofRequest(
        proof_request=IndyProofRequest(**proof_dict["proof_request"]),
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )

    pred_keys = proof_request_v1.proof_request.requested_predicates.keys()
    attr_keys = proof_request_v1.proof_request.requested_attributes.keys()

    proof_request_v1.proof_request.requested_attributes[
        schema_definition.schema_id
    ] = proof_request_v1.proof_request.requested_attributes.pop(list(attr_keys)[0])

    proof_request_v1.proof_request.requested_predicates[
        schema_definition.schema_id
    ] = proof_request_v1.proof_request.requested_predicates.pop(list(pred_keys)[0])

    await register_verifier(alice_member_client, schema_definition.schema_id)

    response = await alice_member_client.post(
        BASE_PATH + "/create-request",
        json=proof_request_v1.dict(),
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v1-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value
    response = await alice_member_client.post(
        BASE_PATH + "/create-request",
        json=proof_request_v2.dict(),
    )

    result = response.json()
    assert "presentation" in result.keys()
    assert "created_at" in result.keys()
    assert "proof_id" in result.keys()
    assert "v2-" in result["proof_id"]
    assert result["role"] == "verifier"
    assert result["state"]


@pytest.mark.asyncio
async def test_accept_proof_request(
    alice_bob_connect_multi: BobAliceConnect,
    alice_member_client: AsyncClient,
    issue_credential_to_bob: CredentialExchange,
    bob_member_client: AsyncClient,
    register_bob_multi: MultiInvite,
    # yoma_client: AcaPyClient,
    schema_definition: SchemaSendResult,
    # bob_and_alice_connection: BobAliceConnect,
):
    # V1
    proof_request_v1 = create_send_request(
<<<<<<< HEAD
        alice_bob_connect_multi["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v10.value,
    )
    proof_request_v1.connection_id = alice_bob_connect_multi["alice_connection_id"]
    proof_dict["connection_id"] = alice_bob_connect_multi["alice_connection_id"]

    pred_keys = proof_request_v1.proof_request.requested_predicates.keys()
    attr_keys = proof_request_v1.proof_request.requested_attributes.keys()

    proof_request_v1.proof_request.requested_attributes[
        schema_definition.schema_id
    ] = proof_request_v1.proof_request.requested_attributes.pop(list(attr_keys)[0])

    proof_request_v1.proof_request.requested_predicates[
        schema_definition.schema_id
    ] = proof_request_v1.proof_request.requested_predicates.pop(list(pred_keys)[0])

    await register_verifier(alice_member_client, schema_definition.schema_id)
    await register_verifier(bob_member_client, schema_definition.schema_id)
=======
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_dict["connection_id"] = bob_and_alice_connection["alice_connection_id"]
>>>>>>> development

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

<<<<<<< HEAD
    time.sleep(3)
    bob_credential_records = (
        await bob_member_client.get(f"/generic/verifier/proofs")
    ).json()
    print(proof_req_res.json())

    print(f"\n\n\nbob proof id: {bob_credential_records[0]['proof_id']}\n\n\n")

    print(f"\n\n\n\nbob cred cred recs: {bob_credential_records}")
    print(f"\n\ncredential bob \n\n {issue_credential_to_bob}")
=======
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

>>>>>>> development
    accept_proof_request_v1 = AcceptProofRequest(
        protocol_version="v1",
        proof_id=bob_credential_records[0]["proof_id"],
        presentation_spec=IndyPresSpec(
            requested_attributes={
                "speed": {
                    "cred_id": issue_credential_to_bob["credential_id"][3:],
                    "revealed": True,
                }
            },
            requested_predicates={
                "speed": {
                    "cred_id": issue_credential_to_bob["credential_id"][3:],
                }
            },
            self_attested_attributes={},
        ),
    )

    response = await bob_member_client.post(
        BASE_PATH + "/accept-request",
        json=accept_proof_request_v1.dict(),
    )
    # # TODO check for the correct response when state is request_received
    result = response.json()
    print(json.dumps(result, indent=4))

<<<<<<< HEAD
    assert result == True

    # V2
    # proof_request_v2 = proof_request_v1
    # proof_request_v2.protocol_version = ProofRequestProtocolVersion.v20.value

    # time.sleep(3)
    # proof_req_res = await alice_member_client.post(
    #     BASE_PATH + "/send-request",
    #     json=proof_request_v2.dict(),
    # )

    # accept_proof_request_v2 = AcceptProofRequest(
    #     protocol_version="v2",
    #     proof_id=proof_req_res.json()["proof_id"],
    #     presentation_spec=indy_pres_spec,
    # )

    # response = await alice_member_client.post(
    #     BASE_PATH + "/accept-request",
    #     json=accept_proof_request_v2.dict(),
    # )
    # # TODO check for the correct response when state is request_received
    # result = response.json()
    # assert response.status_code == 400
    # assert_that(result).contains("detail")
    # assert ("Presentation exchange" and "state (must be request-received)") in result[
    #     "detail"
    # ]
=======
    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    assert response.status_code == 400
    assert_that(result).contains("detail")
    assert ("Presentation exchange" and "state (must be request_received)") in result[
        "detail"
    ]

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    accept_proof_request_v2 = AcceptProofRequest(
        protocol_version="v2",
        proof_id=proof_req_res.json()["proof_id"],
        presentation_spec=indy_pres_spec,
    )

    response = await alice_member_client.post(
        BASE_PATH + "/accept-request",
        json=accept_proof_request_v2.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    # TODO check for the correct response when state is request_received
    result = response.json()
    assert response.status_code == 400
    assert_that(result).contains("detail")
    assert ("Presentation exchange" and "state (must be request-received)") in result[
        "detail"
    ]
>>>>>>> development


@pytest.mark.asyncio
async def test_reject_proof_request(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    response = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    assert check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="present_proof",
    )

    reject_proof_request_v1 = RejectProofRequest(
        proof_id=response.json()["proof_id"], problem_report=None
    )

    response = await alice_member_client.post(
        BASE_PATH + "/reject-request", json=reject_proof_request_v1.dict()
    )
    result = response.json()
    assert result is None


@pytest.mark.asyncio
async def test_get_proof_single(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_dict["connection_id"] = bob_and_alice_connection["alice_connection_id"]
    proof_req_res = await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v1.dict(),
    )

    proof_id = proof_req_res.json()["proof_id"]
    response = await alice_member_client.get(
        f"{BASE_PATH}/proofs/{proof_id}",
    )
    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "presentation_request" in result

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v2.dict(),
    )

    proof_id = proof_req_res.json()["proof_id"]

    response = await alice_member_client.get(
        f"{BASE_PATH}/proofs/{proof_id}",
    )

    result = response.json()
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v2-" in result["proof_id"]
    assert "presentation_request" in result


@pytest.mark.asyncio
async def test_get_proofs_multi(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_dict["connection_id"] = bob_and_alice_connection["alice_connection_id"]
    await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v1.dict(),
    )

    response = await alice_member_client.get(
        f"{BASE_PATH}/proofs",
    )

    result = response.json()[0]
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v1-" in result["proof_id"]
    assert "presentation_request" in result

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    await alice_member_client.post(
        f"{BASE_PATH}/send-request",
        json=proof_request_v2.dict(),
    )

    response = await alice_member_client.get(
        BASE_PATH + "/proofs",
    )

    result = response.json()[-1]
    assert "connection_id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "presentation" in result
    assert "v2-" in result["proof_id"]
    assert "presentation_request" in result


@pytest.mark.asyncio
async def test_delete_proof(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_dict["connection_id"] = bob_and_alice_connection["alice_connection_id"]
    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.delete(
        BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.json() == None

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.delete(
        BASE_PATH + f"/proofs/{proof_id}",
    )
    assert response.json() == None


@pytest.mark.asyncio
async def test_get_credentials_for_request(
    bob_and_alice_connection: BobAliceConnect,
    alice_member_client: AsyncClient,
):
    # V1
    proof_request_v1 = create_send_request(
        bob_and_alice_connection["alice_connection_id"],
        protocol_version=ProofRequestProtocolVersion.v1.value,
    )
    proof_request_v1.connection_id = bob_and_alice_connection["alice_connection_id"]
    proof_dict["connection_id"] = bob_and_alice_connection["alice_connection_id"]
    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v1.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.get(
        f"{BASE_PATH}/credentials/{proof_id}",
    )

    result = response.json()
    assert result == []

    # V2
    proof_request_v2 = proof_request_v1
    proof_request_v2.protocol_version = ProofRequestProtocolVersion.v2.value

    proof_req_res = await alice_member_client.post(
        BASE_PATH + "/send-request",
        json=proof_request_v2.dict(),
    )

    proof_id = (proof_req_res.json())["proof_id"]

    response = await alice_member_client.get(
        f"{BASE_PATH}/credentials/{proof_id}",
    )

    result = response.json()
    assert result == []
