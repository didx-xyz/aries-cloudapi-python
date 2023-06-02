import pytest
from aries_cloudcontroller import AcaPyClient, SignatureOptions
from assertpy import assert_that

from app.error.cloud_api_error import CloudApiException
from app.generic.jsonld.jsonld import JsonLdSignRequest, JsonLdVerifyRequest
from app.tests.e2e.test_fixtures import *
from shared import RichAsyncClient

jsonld_credential = {
    "@context": "https://json-ld.org/contexts/person.jsonld",
    "@id": "http://dbpedia.org/resource/John_Lennon",
    "name": "John Lennon",
    "born": "1940-10-09",
    "spouse": "http://dbpedia.org/resource/Cynthia_Lennon",
}

signed_doc = {
    "doc": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
        ],
        "id": "http://example.edu/credentials/1872",
        "type": ["VerifiableCredential", "AlumniCredential"],
        "issuanceDate": "2010-01-01T19:23:24Z",
        "credentialSubject": {
            "id": "did:example:ebfeb1f712ebc6f1c276e12ec21",
            "alumniOf": {
                "id": "did:example:c276e12ec21ebfeb1f712ebc6f1",
                "name": [
                    {"value": "Example University", "lang": "en"},
                    {"value": "Exemple d'Université", "lang": "fr"},
                ],
            },
        },
        "proof": {
            "type": "Ed25519Signature2018",
            "verificationMethod": "did:key:did:key:z6Mkq8pevWDaxgsD2DZC11JUnnjGdrLmHSh9P7waX3HR4Zwz#did:key:z6Mkq8pevWDaxgsD2DZC11JUnnjGdrLmHSh9P7waX3HR4Zwz",
            "proofPurpose": "assertionMethod",
            "created": "2022-11-24T08:20:11Z",
            "jws": "eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..Rdpq5uOCJInEMD-5G7mXalu0NiJHSgIfE5ISE7Ed451wJmkpFHR50K9Sb3nEo0P8wpXzrUQRCETqImTvqsZNDA",
        },
    },
    "verkey": "BgZcLFy9d9NjuiiVKSLdwhBGpH4usZSnh72egmKQ9MAc",
}


@pytest.mark.anyio
async def test_sign_jsonld(
    alice_member_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_client: RichAsyncClient,
    faber_and_alice_connection: FaberAliceConnect,
    issue_credential_to_alice: CredentialExchange,
):
    json_ld_req = JsonLdSignRequest(
        verkey="abcde",
        pub_did="abcde",
        credential_id=issue_credential_to_alice["credential_id"][3:],
        signature_options=SignatureOptions(
            proof_purpose="test", verification_method="ed25519"
        ).dict(),
    )

    # Error
    with pytest.raises(CloudApiException) as exc:
        await alice_member_client.post("/generic/jsonld/sign", json=json_ld_req.dict())

    assert_that(exc.value.detail).contains(
        "Please provide either or neither, but not both"
    )
    assert_that(exc.value.status_code).is_equal_to(400)

    # Success pub_did
    faber_pub_did = (await faber_acapy_client.wallet.get_public_did()).result.did
    json_ld_req.pub_did = faber_pub_did
    json_ld_req.credential = jsonld_credential
    json_ld_req.credential_id = None
    json_ld_req.verkey = None
    jsonld_sign_response = await faber_client.post(
        "/generic/jsonld/sign", json=json_ld_req.dict()
    )
    assert_that(jsonld_sign_response.status_code).is_equal_to(200)
    jsonld_sign_response = jsonld_sign_response.json()
    assert jsonld_sign_response["signed_doc"]
    assert all(
        item in jsonld_sign_response["signed_doc"].keys()
        for item in jsonld_credential.keys()
    )

    # # Success verkey
    pub_did = (await faber_acapy_client.wallet.get_public_did()).result.did
    faber_verkey = (await faber_acapy_client.ledger.get_did_verkey(did=pub_did)).verkey
    json_ld_req.pub_did = None
    json_ld_req.verkey = faber_verkey

    jsonld_sign_response = await faber_client.post(
        "/generic/jsonld/sign", json=json_ld_req.dict()
    )

    assert_that(jsonld_sign_response.status_code).is_equal_to(200)
    jsonld_sign_response = jsonld_sign_response.json()
    assert jsonld_sign_response["signed_doc"]
    assert all(
        item in jsonld_sign_response["signed_doc"].keys()
        for item in jsonld_credential.keys()
    )

    # Success bare
    json_ld_req.pub_did = None
    json_ld_req.verkey = None

    jsonld_sign_response = await faber_client.post(
        "/generic/jsonld/sign", json=json_ld_req.dict()
    )

    assert_that(jsonld_sign_response.status_code).is_equal_to(200)
    jsonld_sign_response = jsonld_sign_response.json()
    assert jsonld_sign_response["signed_doc"]
    assert all(
        item in jsonld_sign_response["signed_doc"].keys()
        for item in jsonld_credential.keys()
    )


@pytest.mark.anyio
async def test_verify_jsonld(
    alice_member_client: RichAsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_client: RichAsyncClient,
):
    jsonld_verify = JsonLdVerifyRequest(
        public_did="abcde",
        verkey=signed_doc["verkey"],
        doc=signed_doc["doc"],
    )
    # Error wrong args
    with pytest.raises(CloudApiException) as exc:
        response = await alice_member_client.post(
            "/generic/jsonld/verify", json=jsonld_verify.dict()
        )
    assert_that(exc.value.detail).contains(
        "Please provide either, but not both, public did of the verkey or the verkey for the document"
    )
    assert_that(exc.value.status_code).is_equal_to(400)

    # # Error invalid
    jsonld_verify.verkey = None
    faber_pub_did = (await faber_acapy_client.wallet.get_public_did()).result.did
    jsonld_verify.public_did = faber_pub_did

    with pytest.raises(CloudApiException) as exc:
        await faber_client.post("/generic/jsonld/verify", json=jsonld_verify.dict())

    assert_that(exc.value.status_code).is_equal_to(422)
    assert_that(exc.value.detail).contains("Failed to verify payload with")

    # Success
    jsonld_verify.public_did = None
    jsonld_verify.verkey = signed_doc["verkey"]

    response = await alice_member_client.post(
        "/generic/jsonld/verify", json=jsonld_verify.dict()
    )
    assert_that(response.status_code).is_equal_to(204)
