from copy import deepcopy

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
from app.tests.util.ecosystem_connections import FaberAliceConnect
from app.tests.util.trust_registry import DidKey
from shared import RichAsyncClient

CREDENTIALS_BASE_PATH = issuer_router.prefix

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
        options=LDProofVCDetailOptions(proofType="BbsBlsSignature2020"),
    ),
).dict(by_alias=True, exclude_unset=True)

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
async def test_send_jsonld_mismatch_sov_bbs(
    faber_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_and_alice_connection: FaberAliceConnect,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    faber_pub_did = (await faber_acapy_client.wallet.get_public_did()).result.did

    # Creating JSON-LD credential did:sov
    credential = deepcopy(credential_)
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"][
        "issuer"
    ] = f"did:sov:{faber_pub_did}"

    # Send credential must fail did:sov cant issue proofType: BbsBlsSignature2020
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    assert_that(exc.value.status_code).is_equal_to(500)


@pytest.mark.anyio
async def test_send_jsonld_mismatch_bbs_ed(
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    register_key_issuer_bbs: DidKey,
):
    faber_connection_id = faber_and_alice_connection.faber_connection_id

    did = register_key_issuer_bbs

    # Creating JSON-LD credential did:key
    credential = deepcopy(credential_)
    credential["connection_id"] = faber_connection_id
    credential["ld_credential_detail"]["credential"]["issuer"] = f"{did}"
    credential["ld_credential_detail"]["options"] = {
        "proofType": "Ed25519Signature2018"
    }
    # Send credential must fail did:key made with bbs cant issue proofType: Ed25519Signature2018
    with pytest.raises(HTTPException) as exc:
        await faber_client.post(
            CREDENTIALS_BASE_PATH,
            json=credential,
        )
    assert_that(exc.value.status_code).is_equal_to(500)
