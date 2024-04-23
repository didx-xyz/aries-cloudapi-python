import asyncio
from copy import deepcopy

import pytest
from aries_cloudcontroller import Credential, LDProofVCDetail, LDProofVCOptions
from assertpy import assert_that
from fastapi import HTTPException

from app.models.issuer import SendCredential
from app.routes.connections import router as con_router
from app.routes.issuer import router as issuer_router
from app.routes.oob import router as oob_router
from app.tests.util.connections import FaberAliceConnect
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix
OOB_BASE_PATH = oob_router.prefix
CONNECTIONS_BASE_PATH = con_router.prefix

credential_ = SendCredential(
    type="ld_proof",
    connection_id="",
    protocol_version="v2",
    ld_credential_detail=LDProofVCDetail(
        credential=Credential(
            context=[
                "https://www.w3.org/2018/credentials/v1",
                "https://www.w3.org/2018/credentials/examples/v1",
            ],
            type=["VerifiableCredential", "UniversityDegreeCredential"],
            credentialSubject={
                "degree": {
                    "type": "BachelorDegree",
                    "name": "Bachelor of Science and Arts",
                },
                "college": "Faber College",
            },
            issuanceDate="2021-04-12",
            issuer="",
        ),
        options=LDProofVCOptions(proofType="Ed25519Signature2018"),
    ),
).model_dump(by_alias=True, exclude_unset=True)

# This is the json of the above credential
# {
#     "type": "ld_proof",
#     "connection_id": "",
#     "protocol_version": "v2",
#     "ld_credential_detail": {
#         "credential": {
#             "@context": [
#                 "https://www.w3.org/2018/credentials/v1",
#                 "https://www.w3.org/2018/credentials/examples/v1",
#             ],
#             "type": ["VerifiableCredential", "UniversityDegreeCredential"],
#             "credentialSubject": {
#                 "degree": {
#                     "type": "BachelorDegree",
#                     "name": "Bachelor of Science and Arts",
#                 },
#                 "college": "Faber College",
#             },
#             "issuanceDate": "2021-04-12",
#             "issuer": "",
#         },
#         "options": "",
#     },
# }


@pytest.mark.anyio
async def test_send_jsonld_key_ed25519(
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    register_issuer_key_ed25519: str,
):
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    # Updating JSON-LD credential did:key with proofType ed25519
    credential = deepcopy(credential_)
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = register_issuer_key_ed25519

    # Send credential
    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    data = response.json()
    thread_id = data["thread_id"]
    assert_that(data).contains("credential_exchange_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        filter_map={
            "thread_id": thread_id,
        },
    )

    # Check if Alice received the credential
    await asyncio.sleep(0.2)  # credential may take moment to reflect after webhook
    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"thread_id": thread_id},
    )

    records = response.json()

    assert len(records) == 1

    # Check if the received credential matches the sent one
    received_credential = records[-1]
    assert_that(received_credential).has_connection_id(alice_connection_id)
    assert_that(received_credential).has_state("offer-received")
    assert_that(received_credential).has_role("holder")
    assert_that(received_credential["credential_exchange_id"]).starts_with("v2")


@pytest.mark.anyio
async def test_send_jsonld_oob(
    faber_client: RichAsyncClient,
    alice_member_client: RichAsyncClient,
    register_issuer_key_ed25519: str,
):
    invitation_response = await faber_client.post(
        OOB_BASE_PATH + "/create-invitation",
        json={
            "create_connection": True,
            "use_public_did": False,
            "attachments": [],
        },
    )

    invitation = (invitation_response.json())["invitation"]

    accept_response = await alice_member_client.post(
        OOB_BASE_PATH + "/accept-invitation",
        json={"invitation": invitation},
    )

    oob_record = accept_response.json()
    alice_connection_id = oob_record["connection_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        topic="connections",
        state="completed",
        filter_map={
            "connection_id": alice_connection_id,
        },
    )
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")

    faber_con = await faber_client.get(CONNECTIONS_BASE_PATH)

    faber_connections = faber_con.json()
    for con in faber_connections:
        if con["invitation_msg_id"] == invitation["@id"]:
            faber_connection_id = con["connection_id"]

    # Updating JSON-LD credential did:key with proofType ed25519
    credential = deepcopy(credential_)
    credential["connection_id"] = (
        faber_connection_id  # pylint: disable=possibly-used-before-assignment
    )
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = register_issuer_key_ed25519

    # Send credential
    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    data = response.json()
    assert_that(data).contains("credential_exchange_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        filter_map={
            "connection_id": alice_connection_id,
        },
    )


@pytest.mark.anyio
async def test_send_jsonld_request(
    alice_member_client: RichAsyncClient,
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    register_issuer_key_ed25519: str,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    # Updating JSON-LD credential did:key with proofType ed25519
    credential = deepcopy(credential_)
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = register_issuer_key_ed25519

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    thread_id = credential_exchange["thread_id"]
    assert credential_exchange["protocol_version"] == "v2"

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        state="offer-sent",
        filter_map={
            "thread_id": thread_id,
        },
        look_back=5,
    )

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        look_back=5,
    )

    await asyncio.sleep(0.2)  # credential may take moment to reflect after webhook
    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"thread_id": thread_id},
    )

    credential_exchange_id = (response.json())[0]["credential_exchange_id"]

    request_response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{credential_exchange_id}/request",
    )

    assert request_response.status_code == 200

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="request-sent",
        look_back=5,
    )

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        state="request-received",
        look_back=5,
    )


@pytest.mark.anyio
async def test_issue_jsonld_ed(
    alice_member_client: RichAsyncClient,
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    register_issuer_key_ed25519: str,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    # Updating JSON-LD credential did:key with proofType ed25519
    credential = deepcopy(credential_)
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = register_issuer_key_ed25519

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    thread_id = credential_exchange["thread_id"]
    assert credential_exchange["protocol_version"] == "v2"

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        state="offer-sent",
        filter_map={
            "thread_id": thread_id,
        },
        look_back=5,
    )

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="offer-received",
        look_back=5,
    )

    await asyncio.sleep(0.2)  # credential may take moment to reflect after webhook
    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"thread_id": thread_id},
    )

    credential_exchange_id = (response.json())[0]["credential_exchange_id"]

    request_response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{credential_exchange_id}/request",
    )

    assert request_response.status_code == 200

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        state="done",
        look_back=5,
    )

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        state="done",
        look_back=5,
    )


# Fail cases:


@pytest.mark.anyio
async def test_send_jsonld_mismatch_ed_bbs(
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    register_issuer_key_ed25519: str,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    # Creating JSON-LD credential did:key with proofType: BbsBlsSignature2020
    credential = deepcopy(credential_)
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = register_issuer_key_ed25519
    credential["ld_credential_detail"]["options"] = {"proofType": "BbsBlsSignature2020"}

    # Send credential must fail did:key made with ed25519 mismatch with proofType:BbsBlsSignature2020
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    assert exc.value.status_code == 400
