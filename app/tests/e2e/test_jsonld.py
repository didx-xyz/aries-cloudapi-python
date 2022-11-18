from aries_cloudcontroller import AcaPyClient, SignatureOptions, SignedDoc
import pytest
from assertpy import assert_that
from httpx import AsyncClient
from app.generic.jsonld.jsonld import JsonLdSignRequest, JsonLdVerifyRequest
from app.tests.util.ecosystem_personas import AcmeAliceConnect
from app.tests.e2e.test_fixtures import *

from shared_models.shared_models import CredentialExchange


@pytest.mark.asyncio
async def test_sign_jsonld(
    alice_member_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
    # governance_acapy_client: AcaPyClient,
    acme_client: AsyncClient,
    acme_and_alice_connection: AcmeAliceConnect,
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
    # await governance_acapy_client.
    alice_pub_did = (await alice_acapy_client.wallet.get_public_did()).result.did
    json_ld_req.pub_did = alice_pub_did
    json_ld_req.verkey = None

    jsonld_sign_response = await alice_member_client.post(
        "/generic/jsonld/sign", json=json_ld_req.dict()
    )

    assert_that(jsonld_sign_response.status_code).is_equal_to(200)
    jsonld_sign_response = jsonld_sign_response.json()

    # # Success verkey
    # alice_verkey = (await alice_acapy_client.ledger.get_did_verkey()).verkey
    # json_ld_req.pub_did = None
    # json_ld_req.verkey = alice_verkey

    # response = await alice_member_client.post(
    #     "/generic/jsonld/sign", json=json_ld_req.dict()
    # )

    # assert_that(response.status_code).is_equal_to(200)
    # assert_that(response.json()).contains("error", "signed_doc")

    # Success bare
    # json_ld_req.pub_did = None
    # json_ld_req.verkey = None
    # response = await alice_member_client.post(
    #     "/generic/jsonld/sign", json=json_ld_req.dict()
    # )

    # assert_that(response.status_code).is_equal_to(200)
    # assert_that(response.json()).contains("error", "signed_doc")


@pytest.mark.asyncio
async def test_verify_jsonld(
    alice_member_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
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
