from aries_cloudcontroller import AcaPyClient
import pytest
from httpx import AsyncClient

from shared_models.shared_models import CredentialExchange


@pytest.mark.asyncio
async def test_sign_jsonld(
    alice_member_client: AsyncClient,
    issue_credential_to_alice: CredentialExchange,
):
    pass
    # json_ld_req = JsonLdSignRequest(
    #     credential_id=issue_credential_to_alice.credential_id[3:],
    #     signature_options=SignatureOptions(proof_purpose="test"),
    # )
    # jsonld_sign_response = await alice_member_client.post(
    #     "/generic/jsonld/sign", json=json_ld_req.json()
    # )
    # assert_that(jsonld_sign_response.status_code).is_equal_to(200)
    # jsonld_sign_response = jsonld_sign_response.json()

    # assert_that(jsonld_sign_response).contains("error", "signed_doc")


@pytest.mark.asyncio
async def test_verify_jsonld(
    alice_member_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
):
    pass
