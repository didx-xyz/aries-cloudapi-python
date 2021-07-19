import json
import random
import string
from contextlib import asynccontextmanager

from admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_created_credential_definitions,
    get_credential_definition,
)
from admin.governance.schemas import SchemaDefinition, create_schema
from assertpy import assert_that
from tests.admin.governance.schemas.test_schemas import create_public_did
from tests.utils_test import get_random_string

import dependencies
import pytest
from generic.issuers_v1 import (
    get_records,
    get_x_record,
    remove_credential,
    problem_report,
    send_offer,
    send_credential_request,
    store_credential,
    send_credential_proposal,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/generic/connections"
CREATE_WALLET_PAYLOAD_YODA = {
    "image_url": "https://aries.ca/images/sample.png",
    "key_management_mode": "managed",
    "label": "YOMA",
    "wallet_dispatch_type": "default",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "YodaJediPokerFunds",
    "wallet_type": "indy",
}
CREATE_WALLET_PAYLOAD_HAN = {
    "image_url": "https://aries.ca/images/sample.png",
    "key_management_mode": "managed",
    "label": "YOMA",
    "wallet_dispatch_type": "default",
    "wallet_key": "MySecretKey1234",
    "wallet_name": "HanSolosCocktailFunds",
    "wallet_type": "indy",
}


# async def remove_wallets(yoda_wallet_id, han_wallet_id, async_client):
#     yoda_response = await async_client.delete(
#         f"/admin/wallet-multitenant/{yoda_wallet_id}",
#         headers={"x-api-key": "adminApiKey", "x-role": "member"},
#     )
#     han_response = await async_client.delete(
#         f"/admin/wallet-multitenant/{han_wallet_id}",
#         headers={"x-api-key": "adminApiKey", "x-role": "member"},
#     )
#     return yoda_response, han_response


async def create_credential(yoma_agent_mock):
    definition = SchemaDefinition(
        name="test_schema", version="0.3", attributes=["average"]
    )

    public_did = await create_public_did(yoma_agent_mock)
    print(f" created did:{public_did}")
    schema_definition_result = await create_schema(definition, yoma_agent_mock)
    print(schema_definition_result)

    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = await create_credential_definition(credential_definition, yoma_agent_mock)

    # then
    written = await get_credential_definition(
        result["credential_definition_id"], yoma_agent_mock
    )

    return written


# async def invite_creation(async_client, token, wallet_id):
#     invite_creation_response = await async_client.get(
#         "/generic/connections/create-invite",
#         headers={
#             "authorization": f"Bearer {token}",
#             "x-wallet-id": wallet_id,
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#     )
#     return invite_creation_response.json()["invitation"]


# async def token_responses(async_client, create_wallets_mock):
#     yoda, han = create_wallets_mock

#     yoda_wallet_id = yoda["wallet_id"]
#     han_wallet_id = han["wallet_id"]

#     yoda_token_response = await async_client.get(
#         f"/admin/wallet-multitenant/{yoda_wallet_id}/auth-token",
#         headers={
#             "x-api-key": "adminApiKey",
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#     )

#     han_token_response = await async_client.get(
#         f"/admin/wallet-multitenant/{han_wallet_id}/auth-token",
#         headers={
#             "x-api-key": "adminApiKey",
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#     )
#     yoda_token = yoda_token_response.json()["token"]
#     han_token = han_token_response.json()["token"]
#     return yoda_token, yoda_wallet_id, han_token, han_wallet_id


# @pytest.fixture(name="create_wallets_mock")
# async def fixture_create_wallets_mock(async_client):
#     # Create two wallets
#     gen_random_length = 42
#     CREATE_WALLET_PAYLOAD_HAN["wallet_name"] = "".join(
#         random.choice(string.ascii_uppercase + string.digits)  # NOSONAR # nolint
#         for _ in range(gen_random_length)  # NOSONAR # nolint
#     )
#     CREATE_WALLET_PAYLOAD_YODA["wallet_name"] = "".join(
#         random.choice(string.ascii_uppercase + string.digits)  # NOSONAR # nolint
#         for _ in range(gen_random_length)  # NOSONAR # nolint
#     )

#     yoda_wallet_response = await async_client.post(
#         "/admin/wallet-multitenant/create-wallet",
#         headers={
#             "x-api-key": "adminApiKey",
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#         data=json.dumps(CREATE_WALLET_PAYLOAD_YODA),
#     )
#     yoda_wallet_response = yoda_wallet_response.json()
#     yoda_wallet_id = yoda_wallet_response["wallet_id"]
#     han_wallet_response = await async_client.post(
#         "/admin/wallet-multitenant/create-wallet",
#         headers={
#             "x-api-key": "adminApiKey",
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#         data=json.dumps(CREATE_WALLET_PAYLOAD_HAN),
#     )
#     han_wallet_response = han_wallet_response.json()
#     han_wallet_id = han_wallet_response["wallet_id"]
#     yield yoda_wallet_response, han_wallet_response

#     yoda_response, han_response = await remove_wallets(
#         yoda_wallet_id, han_wallet_id, async_client
#     )
#     assert yoda_response.status_code == 200
#     assert yoda_response.json() == {"status": "Successfully removed wallet"}
#     assert han_response.status_code == 200
#     assert han_response.json() == {"status": "Successfully removed wallet"}


# @pytest.fixture(scope="session", autouse=True)
# async def create_credential_records(yoma_agent_mock):
#     pass


@pytest.mark.asyncio
async def test_send_offer(yoma_agent_mock):
    cred_res = await create_credential(yoma_agent_mock)


@pytest.mark.asyncio
async def test_get_credential(yoma_agent_mock):
    credential_res = await create_credential(yoma_agent_mock)
    # assert credential_res == ""
    cred_id = credential_res["credential_definition"]["id"]
    assert cred_id == ""


#     got_credential = await get_credential(cred_id, yoma_agent_mock)
#     assert got_credential == ''


# @pytest.mark.asyncio
# async def test_get_records(yoma_agent_mock):
#     # credential = await create_credential(yoma_agent_mock)
#     records = await get_records(yoma_agent_mock)
#     assert type(records) == dict
#     assert "results" in records.keys()
#     assert type(records["results"]) is list

# @pytest.mark.asyncio
# async def test_send_credential(async_client, create_wallets_mock):
#     yoda, han = create_wallets_mock

#     yoda_wallet_id = yoda["wallet_id"]
#     han_wallet_id = han["wallet_id"]

#     yoda_token_response = await async_client.get(
#         f"/admin/wallet-multitenant/{yoda_wallet_id}/auth-token",
#         headers={
#             "x-api-key": "adminApiKey",
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#     )

#     yoda_token = yoda_token_response.json()["token"]

#     han_token_response = await async_client.get(
#         f"/admin/wallet-multitenant/{han_wallet_id}/auth-token",
#         headers={
#             "x-api-key": "adminApiKey",
#             "x-role": "member",
#             **APPLICATION_JSON_CONTENT_TYPE,
#         },
#     )

#     han_token = han_token_response.json()["token"]

#     async with asynccontextmanager(dependencies.member_agent)(
#         authorization=f"Bearer {yoda_token}", x_wallet_id=yoda_wallet_id
#     ) as member_agent:
#         invite_creation_response = await create_invite(member_agent)
#     assert (
#         invite_creation_response["connection_id"]
#         and invite_creation_response["connection_id"] != {}
#     )
#     assert (
#         invite_creation_response["invitation"]
#         and invite_creation_response["invitation"] != {}
#     )
#     assert (
#         invite_creation_response["invitation"]["@id"]
#         and invite_creation_response["invitation"]["@id"] != {}
#     )
