import pytest
from aries_cloudcontroller import (
    AcaPyClient,
    Credential,
    LDProofVCDetail,
    LDProofVCDetailOptions,
)
from assertpy import assert_that
from fastapi import HTTPException

from app.models.issuer import SendCredential
from app.routes.issuer import router as issuer_router
from app.routes.oob import router as oob_router
from app.routes.wallet import router as wallet_router
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.trust_registry import DidKey
from app.tests.util.webhooks import check_webhook_state
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix
OOB_BASE_PATH = oob_router.prefix
WALLET = wallet_router.prefix

# This is the json of the below credential
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

credential = SendCredential(
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
        options=LDProofVCDetailOptions(proofType=""),
    ),
).dict(by_alias=True, exclude_unset=True)


@pytest.mark.anyio
@pytest.mark.parametrize("register_key_issuer", ["bls12381g2"], indirect=True)
async def test_send_jsonld_key_bbs(
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    register_key_issuer: DidKey,
):
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    did = register_key_issuer

    # Creating JSON-LD credential did:key
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"]["issuer"] = f"{did}"
    credential["ld_credential_detail"]["options"] = {"proofType": "BbsBlsSignature2020"}

    # Send credential
    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")

    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        filter_map={
            "state": "offer-received",
            "connection_id": alice_connection_id,
        },
    )

    # Check if Alice received the credential
    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": alice_connection_id},
    )

    records = response.json()

    assert len(records) == 1

    # Check if the received credential matches the sent one
    received_credential = records[-1]
    assert_that(received_credential).has_connection_id(alice_connection_id)
    assert_that(received_credential).has_state("offer-received")
    assert_that(received_credential).has_role("holder")
    assert_that(received_credential["credential_id"]).starts_with("v2")


@pytest.mark.anyio
async def test_send_jsonld_mismatch_sov_bbs(
    faber_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_and_alice_connection: FaberAliceConnect,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    faber_pub_did = (await faber_acapy_client.wallet.get_public_did()).result.did

    # Creating JSON-LD credential did:sov
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = f"did:sov:{faber_pub_did}"
    credential["ld_credential_detail"]["options"] = {"proofType": "BbsBlsSignature2020"}

    # Send credential must fail did:sov cant issue proofType: BbsBlsSignature2020
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    assert_that(exc.value.status_code).is_equal_to(500)


@pytest.mark.anyio
@pytest.mark.parametrize("register_key_issuer", ["bls12381g2"], indirect=True)
async def test_send_jsonld_mismatch_bbs_ed(
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    register_key_issuer: DidKey,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    did = register_key_issuer

    # Creating JSON-LD credential did:sov
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"]["issuer"] = f"{did}"
    credential["ld_credential_detail"]["options"] = {
        "proofType": "Ed25519Signature2018"
    }
    # Send credential must fail did:sov cant issue proofType: BbsBlsSignature2020
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    assert_that(exc.value.status_code).is_equal_to(500)


@pytest.mark.anyio
@pytest.mark.parametrize("register_key_issuer", ["bls12381g2"], indirect=True)
async def test_send_jsonld_bbs_oob(
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    alice_member_client: RichAsyncClient,
    register_key_issuer: DidKey,
):
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": alice_connection_id},
    )
    records = response.json()

    # nothing currently in alice's records
    assert len(records) == 0
    did = register_key_issuer

    # Updating JSON-LD credential did:sov
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"]["issuer"] = f"{did}"
    credential["ld_credential_detail"]["options"] = {"proofType": "BbsBlsSignature2020"}

    # faber create offer
    response = await faber_client.post(
        CREDENTIALS_BASE_PATH + "/create-offer",
        json=credential,
    )

    data = response.json()
    assert_that(data).contains("credential_id")
    assert_that(data).has_state("offer-sent")
    assert_that(data).has_protocol_version("v2")

    invitation_response = await faber_client.post(
        OOB_BASE_PATH + "/create-invitation",
        json={
            "create_connection": False,
            "use_public_did": False,
            "attachments": [
                {"id": data["credential_id"][3:], "type": "credential-offer"}
            ],
        },
    )
    assert_that(invitation_response.status_code).is_equal_to(200)

    invitation = (invitation_response.json())["invitation"]

    accept_response = await alice_member_client.post(
        OOB_BASE_PATH + "/accept-invitation",
        json={"invitation": invitation},
    )

    oob_record = accept_response.json()

    assert_that(accept_response.status_code).is_equal_to(200)
    assert_that(oob_record).contains("created_at", "oob_id", "invitation")
    assert await check_webhook_state(
        client=alice_member_client,
        topic="credentials",
        filter_map={
            "state": "offer-received",
        },
    )


@pytest.mark.anyio
@pytest.mark.parametrize("register_key_issuer", ["bls12381g2"], indirect=True)
async def test_send_jsonld_request(
    alice_member_client: RichAsyncClient,
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    register_key_issuer: DidKey,
):
    alice_connection_id = faber_and_alice_connection.alice_connection_id
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    did = register_key_issuer

    # Updating JSON-LD credential did:key with proofType bbs
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"]["issuer"] = f"{did}"
    credential["ld_credential_detail"]["options"] = {"proofType": "BbsBlsSignature2020"}

    response = await faber_client.post(
        CREDENTIALS_BASE_PATH,
        json=credential,
    )
    credential_exchange = response.json()
    assert credential_exchange["protocol_version"] == "v2"

    assert await check_webhook_state(
        client=faber_client,
        topic="credentials",
        filter_map={
            "state": "offer-sent",
            "credential_id": credential_exchange["credential_id"],
        },
    )

    response = await alice_member_client.get(
        CREDENTIALS_BASE_PATH,
        params={"connection_id": alice_connection_id},
    )

    credential_id = (response.json())[0]["credential_id"]

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "offer-received"},
        topic="credentials",
    )

    request_response = await alice_member_client.post(
        f"{CREDENTIALS_BASE_PATH}/{credential_id}/request",
    )

    assert request_response.status_code == 200

    assert await check_webhook_state(
        client=alice_member_client,
        filter_map={"state": "request-sent"},
        topic="credentials",
    )

    assert await check_webhook_state(
        client=faber_client,
        filter_map={"state": "request-received"},
        topic="credentials",
    )
