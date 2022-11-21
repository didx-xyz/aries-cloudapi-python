from typing import Any
from aries_cloudcontroller import AcaPyClient, SignatureOptions
import pytest
from assertpy import assert_that
from httpx import AsyncClient
from app.generic.jsonld.jsonld import JsonLdSignRequest
from app.tests.e2e.test_fixtures import * 
from app.tests.e2e.test_fixtures import FaberAliceConnect, BASE_PATH
# from shared_models.shared_models import CredentialExchange



@pytest.mark.asyncio
async def test_sign_jsonld(
    alice_member_client: AsyncClient,
    alice_acapy_client: AcaPyClient,
    # governance_acapy_client: AcaPyClient,
    # acme_client: AsyncClient,
    # acme_and_alice_connection: AcmeAliceConnect,
    issue_credential_to_alice: CredentialExchange,
    # faber_client: AsyncClient,
    # credential_definition_id: str,
    # alice_tenant: Any,
    # faber_and_alice_connection: FaberAliceConnect,
):
    
    
    recos = (await alice_member_client.get(f'{BASE_PATH}')).json()
    print("\n\n\n")
    print(recos)
    print("\n\n\n")
    # assert check_webhook_state(
    #     client=alice_member_client,
    #     filter_map={"state": "done", "credential_id": recos[0]['credential_id']},
    #     topic="credentials",
    #     max_duration=240,
    # )
    recos = (await alice_member_client.get(f'{BASE_PATH}')).json()
    print("\n\n\n")
    print(recos)
    print("\n\n\n")
    reco = [r for r in recos if r['state'] == 'done'][0]
    # Alice stores credential
    # response = await alice_member_client.post(f"{BASE_PATH}/{reco.credential_id}/store")

    # # Check alice has received the credential
    # assert check_webhook_state(
    #     client=alice_member_client,
    #     filter_map={"state": "done"},
    #     topic="credentials",
    #     max_duration=240,
    # )
    
    print("\n\n\n")
    print(response.json())
    print("\n\n\n")
    credential_id = reco['credential_id']

    creds = (
        await alice_member_client.get("/generic/issuer/credentials")
    ).json()
    print("\n\n\n")
    print(creds)
    print("\n\n\n")
    
    
    
    json_ld_req = JsonLdSignRequest(
        verkey="abcde",
        pub_did="abcde",
        credential_id=credential_id[3:],
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
    # credential = {
    #     "protocol_version": "v1",
    #     "credential_definition_id": credential_definition_id,
    #     "connection_id": faber_and_alice_connection["faber_connection_id"],
    #     "attributes": {"speed": "10"},
    # }

    # response = await faber_client.post(
    #     BASE_PATH,
    #     json=credential,
    # )
    # credential_exchange = response.json()
    # assert credential_exchange["protocol_version"] == "v1"

    # assert check_webhook_state(
    #     client=faber_client,
    #     filter_map={
    #         "state": "offer-sent",
    #         "credential_id": credential_exchange["credential_id"],
    #     },
    #     topic="credentials",
    # )

    # response = await alice_member_client.get(
    #     BASE_PATH,
    #     params={"connection_id": faber_and_alice_connection["alice_connection_id"]},
    # )
    # assert check_webhook_state(
    #     client=alice_member_client,
    #     filter_map={"state": "offer-received"},
    #     topic="credentials",
    #     max_duration=240,
    # )

    # cred_hooks = get_hooks_per_topic_per_wallet(
    #     client=alice_member_client, topic="credentials"
    # )

    # cred_hook = [h for h in cred_hooks if h["payload"]["state"] == "offer-received"][0]
    # credential_id = cred_hook["payload"]["credential_id"]

    # # alice send request for that credential
    # response = await alice_member_client.post(f"{BASE_PATH}/{credential_id}/request")
    # response.raise_for_status()

    # # Bob check he received the request; Credential is send because of using
    # # 'automating the entire flow' send credential earlier.
    # # See also: app/generic/issuer/issuer.py::send_credential
    # assert check_webhook_state(
    #     client=faber_client,
    #     filter_map={"state": "request-received"},
    #     topic="credentials",
    #     max_duration=240,
    # )

    # # Check alice has received the credential
    # assert check_webhook_state(
    #     client=alice_member_client,
    #     filter_map={"state": "credential-received"},
    #     topic="credentials",
    #     max_duration=240,
    # )

    
    json_ld_req.credential_id = [c for c in creds if c['state'] == 'done'][-1]["credential_id"][3:]
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


# @pytest.mark.asyncio
# async def test_verify_jsonld(
#     alice_member_client: AsyncClient,
#     alice_acapy_client: AcaPyClient,
# ):
#     jsonld_verify = JsonLdVerifyRequest(
#         their_pub_did="abcde",
#         verkey="verkey",
#         signed_doc=SignedDoc(
#             proof=SignatureOptions(proof_purpose="test", verification_method="ed25519")
#         ).dict(),
#     )
#     # Error
#     response = await alice_member_client.post(
#         "/generic/jsonld/verify", json=jsonld_verify.dict()
#     )
#     assert_that(response.json()["detail"]).contains(
#         "Please provide either, but not both, public did of the verkey or the verkey for the document"
#     )
#     assert_that(response.status_code).is_equal_to(418)
