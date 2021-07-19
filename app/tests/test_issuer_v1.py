# from generic.issuers_v1 import send_credential
import json
import time
from assertpy import assert_that
from contextlib import asynccontextmanager

from admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_created_credential_definitions,
    get_credential_definition,
)
from acapy_ledger_facade import create_pub_did
from admin.governance.schemas import SchemaDefinition, create_schema
from assertpy import assert_that
from tests.admin.governance.schemas.test_schemas import create_public_did
from tests.utils_test import get_random_string

import dependencies
import pytest
from generic.issuers_v1 import (
    get_records,
    get_x_record,
    send_credential,
    remove_credential,
    problem_report,
    send_offer,
    send_credential_request,
    store_credential,
    send_credential_proposal,
    CredentialHelper,
    CredentialOffer,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/generic/issuers/v1"
BASE_PATH_CON = "/generic/connections"


@pytest.fixture
@pytest.mark.asyncio
async def create_bob_and_alice_connect(async_client_bob, async_client_alice):
    """this test validates that bob and alice connect successfully...

    NB: it assumes you have all the "auto connection" settings flagged as on.

    ACAPY_AUTO_ACCEPT_INVITES=true
    ACAPY_AUTO_ACCEPT_REQUESTS=true
    ACAPY_AUTO_PING_CONNECTION=true

    """
    # creaet invitation on bob side
    invitation = (await async_client_bob.get(BASE_PATH_CON + "/create-invite")).json()
    bob_connection_id = invitation["connection_id"]
    connections = (await async_client_bob.get(BASE_PATH_CON)).json()
    assert_that(connections["results"]).extracting("connection_id").contains_only(
        bob_connection_id
    )

    # accept invitation on alice side
    invite_response = (
        await async_client_alice.post(
            BASE_PATH_CON + "/accept-invite", data=json.dumps(invitation["invitation"])
        )
    ).json()
    time.sleep(10)
    alice_connection_id = invite_response["connection_id"]
    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    # and we are running in "auto connect" mode.
    bob_connections = (await async_client_bob.get(BASE_PATH_CON)).json()
    alice_connections = (await async_client_alice.get(BASE_PATH_CON)).json()

    assert_that(bob_connections["results"]).extracting("connection_id").contains(
        bob_connection_id
    )
    bob_connection = [
        c for c in bob_connections["results"] if c["connection_id"] == bob_connection_id
    ][0]
    assert_that(bob_connection).has_state("active")

    assert_that(alice_connections["results"]).extracting("connection_id").contains(
        alice_connection_id
    )
    alice_connection = [
        c
        for c in alice_connections["results"]
        if c["connection_id"] == alice_connection_id
    ][0]
    assert_that(alice_connection).has_state("active")

    return alice_connection_id, bob_connection_id


@pytest.fixture
@pytest.mark.asyncio
async def create_credential_def(yoma_agent_mock):
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
    #     print(written)
    return credential_definition


async def send_credential_helper(
    async_client_bob,
    async_client_alice,
    create_bob_and_alice_connect,
    member_alice,
    create_credential_def,
):
    ida, _ = create_bob_and_alice_connect
    cred_def = create_credential_def
    cred_alice = CredentialHelper(
        connection_id=ida,
        schema_id=cred_def.schema_id,
        credential_attrs=["some_avg"],
    )
    return (
        await async_client_alice.post(BASE_PATH + "/credential", data=cred_alice.json())
    ).json()


@pytest.mark.asyncio
async def test_send_credential(
    async_client_alice, create_bob_and_alice_connect, create_credential_def
):
    ida, _ = create_bob_and_alice_connect
    cred_def = create_credential_def
    cred_alice = CredentialHelper(
        connection_id=ida,
        schema_id=cred_def.schema_id,
        credential_attrs=["some_avg"],
    )
    cred_send_res = (
        await async_client_alice.post(BASE_PATH + "/credential", data=cred_alice.json())
    ).json()
    assert cred_send_res == ""


#     async with asynccontextmanager(dependencies.member_agent)(
#         authorization=f"Bearer {member_alice.token}", x_wallet_id=member_alice.wallet_id
#     ) as member_agent:
#     pub_did_res = await create_pub_did(authorization=f"Bearer {member_alice.token}", x_wallet_id=member_alice.wallet_id)
#     send_cred_res = await send_credential(cred_alice, authorization=f"Bearer {member_alice.token}", x_wallet_id=member_alice.wallet_id)
#     assert send_cred_res

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


# @pytest.mark.asyncio
# async def test_send_offer(yoma_agent_mock):
#     cred_res = await create_credential(yoma_agent_mock)
#     # {'schema_id': '941ZBzvEa3XaWfYhebV2bv:2:test_schema:0.3', 'schema': {'ver': '1.0', 'id': '941ZBzvEa3XaWfYhebV2bv:2:test_schema:0.3', 'name': 'test_schema', 'version': '0.3', 'attrNames': ['average'], 'seqNo': 11222}}
#     cred_res

# @pytest.mark.asyncio
# async def test_get_credential(yoma_agent_mock):
#     credential_res = await create_credential(yoma_agent_mock)
#     # assert credential_res == ""
#     cred_id = credential_res['credential_definition']['id']
#     assert cred_id == ''
#     got_credential = await get_credential(cred_id, yoma_agent_mock)
#     assert got_credential == ''


@pytest.mark.asyncio
async def test_get_records(yoma_agent_mock):
    # credential = await create_credential(yoma_agent_mock)
    records = await get_records(yoma_agent_mock)
    assert type(records) == dict
    assert "results" in records.keys()
    assert type(records["results"]) is list


# @pytest.mark.asyncio
# async def test_send_credential(async_client, create_wallets_mock, cre):
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
