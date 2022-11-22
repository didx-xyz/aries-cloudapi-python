from aries_cloudcontroller import AcaPyClient, SignatureOptions, SignedDoc
import pytest
from assertpy import assert_that
from httpx import AsyncClient
from app.generic.jsonld.jsonld import JsonLdSignRequest, JsonLdVerifyRequest
from app.tests.e2e.test_fixtures import *
from app.tests.e2e.test_fixtures import FaberAliceConnect, BASE_PATH

# from shared_models.shared_models import CredentialExchange

jsonld_credential = {
    "@context": "https://json-ld.org/contexts/person.jsonld",
    "@id": "http://dbpedia.org/resource/John_Lennon",
    "name": "John Lennon",
    "born": "1940-10-09",
    "spouse": "http://dbpedia.org/resource/Cynthia_Lennon",
}


@pytest.mark.asyncio
async def test_sign_jsonld(
    alice_member_client: AsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_client: AsyncClient,
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
    response = await alice_member_client.post(
        "/generic/jsonld/sign", json=json_ld_req.dict()
    )

    assert_that(response.json()["detail"]).contains(
        "Please provide either or neither, but not both"
    )
    assert_that(response.status_code).is_equal_to(418)

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


@pytest.mark.asyncio
async def test_verify_jsonld(
    alice_member_client: AsyncClient,
    faber_acapy_client: AcaPyClient,
    faber_client: AsyncClient,
    issue_credential_to_alice: CredentialExchange,
):
    jsonld_verify = JsonLdVerifyRequest(
        their_pub_did="abcde",
        verkey="verkey",
        signed_doc=SignedDoc(
            proof=SignatureOptions(proof_purpose="test", verification_method="ed25519")
        ).dict(),
    )
    # Error
    response = await alice_member_client.post(
        "/generic/jsonld/verify", json=jsonld_verify.dict()
    )
    assert_that(response.json()["detail"]).contains(
        "Please provide either, but not both, public did of the verkey or the verkey for the document"
    )
    assert_that(response.status_code).is_equal_to(418)
    json_ld_req = JsonLdSignRequest(
        verkey="abcde",
        pub_did="abcde",
        credential_id=issue_credential_to_alice["credential_id"][3:],
        signature_options=SignatureOptions(
            proof_purpose="test", verification_method="ed25519"
        ).dict(),
    )
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

    jsonld_verify.signed_doc = jsonld_sign_response["signed_doc"]
    jsonld_verify.verkey = None
    jsonld_verify.their_pub_did = faber_pub_did

    response = await alice_member_client.post(
        "/generic/jsonld/verify", json=jsonld_verify.dict()
    )
    assert_that(response.status_code).is_equal_to(200)
    # FIXME: Aca-py returns not enough values to unpack (expected 1, got 0) even for a presumably valid jsonld
    # Example taken from aca-py aries_cloudagent/messaging/jsonld/tests/test_routes.py mock_sign_request() and request_body()
    assert_that(response.json()["valid"]).is_equal_to(False)
    assert_that(response.json()["error"]).is_equal_to(
        "not enough values to unpack (expected 1, got 0)"
    )

    # Success verkey
    faber_verkey = (
        await faber_acapy_client.ledger.get_did_verkey(did=faber_pub_did)
    ).verkey
    jsonld_verify.verkey = faber_verkey
    jsonld_verify.their_pub_did = None

    response = await alice_member_client.post(
        "/generic/jsonld/verify", json=jsonld_verify.dict()
    )
    assert_that(response.status_code).is_equal_to(200)
    # FIXME: Aca-py returns not enough values to unpack (expected 1, got 0) even for a presumably valid jsonld
    # Example taken from aca-py aries_cloudagent/messaging/jsonld/tests/test_routes.py mock_sign_request() and request_body()
    assert_that(response.json()["valid"]).is_equal_to(False)
    assert_that(response.json()["error"]).is_equal_to(
        "not enough values to unpack (expected 1, got 0)"
    )
