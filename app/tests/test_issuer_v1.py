# from generic.issuers_v1 import send_credential
import json
import time
from assertpy import assert_that

from admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_credential_definition,
)
from admin.governance.schemas import SchemaDefinition, create_schema
from assertpy import assert_that
from tests.admin.governance.schemas.test_schemas import create_public_did
from tests.utils_test import get_random_string

import pytest
from generic.issuers_v1 import (
    CredentialHelper,
    get_records,
)

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/generic/issuers/v1"
BASE_PATH_CON = "/generic/connections"
SCHEMA_DEFINITION_RESULT = {}
ALICE_CONNECTION_ID = ""
BOB_CONNECTION_ID = ""
CRED_DEF_ID = ""
CRED_X_ID = ""


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
    global ALICE_CONNECTION_ID, BOB_CONNECTION_ID
    ALICE_CONNECTION_ID = alice_connection_id
    BOB_CONNECTION_ID = bob_connection_id
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
    global CRED_DEF_ID
    CRED_DEF_ID = written["credential_definition"]["id"]
    global SCHEMA_DEFINITION_RESULT
    SCHEMA_DEFINITION_RESULT = schema_definition_result
    return credential_definition


@pytest.mark.asyncio
async def test_send_credential(
    async_client_alice, create_bob_and_alice_connect, create_credential_def
):
    cred_alice = CredentialHelper(
        connection_id=ALICE_CONNECTION_ID,
        schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
        credential_attrs=["average"],
    ).json()
    cred_send_res = (
        await async_client_alice.post(BASE_PATH + "/credential", data=cred_alice)
    ).json()
    global CRED_X_ID
    CRED_X_ID = cred_send_res["credential"]["credential_exchange_id"]
    assert cred_send_res["credential"]
    assert cred_send_res["credential"]["connection_id"] == ALICE_CONNECTION_ID
    assert (
        cred_send_res["credential"]["schema_id"]
        == SCHEMA_DEFINITION_RESULT["schema_id"]
    )


# @pytest.mark.asyncio
# async def test_get_x_record(
#     async_client_alice, create_bob_and_alice_connect, create_credential_def
# ):
#     print(CRED_X_ID)
#     headers = async_client_alice.headers.update({"credential-x-id": CRED_X_ID})
#     x_rec_res = (
#         await async_client_alice.get(BASE_PATH + "/credential", headers=headers)
#     ).json()
#     assert x_rec_res == ""


@pytest.mark.asyncio
async def test_send_offer():
    pass


@pytest.mark.asyncio
async def test_send_proposal():
    pass


@pytest.mark.asyncio
async def test_store_credential():
    pass


@pytest.mark.asyncio
async def test_send_request():
    pass


@pytest.mark.asyncio
async def test_send_offer():
    pass


@pytest.mark.asyncio
async def test_problem_report():
    pass


@pytest.mark.asyncio
async def test_get_records(yoma_agent_mock):
    records = await get_records(yoma_agent_mock)
    assert type(records) == dict
    assert "results" in records.keys()
    assert type(records["results"]) is list


# @pytest.mark.asyncio
# async def test_delete_record(
#     async_client_alice, create_bob_and_alice_connect, create_credential_def
# ):
#     print(CRED_DEF_ID)
#     headers = async_client_alice.header.update({"credential-id": CRED_DEF_ID})
#     x_rec_res = (
#         await async_client_alice.delete(BASE_PATH + "/credential", headers=headers)
#     ).json()
#     assert x_rec_res['credential'] == ""

# @pytest.mark.asyncio
# async def test_store_credential(
#     async_client_bob, create_bob_and_alice_connect, create_credential_def
# ):
#     print(CRED_DEF_ID)
#     print(CRED_X_ID)
#     headers = async_client_bob.headers.update({"credential-id": CRED_DEF_ID, "credential-x-id": CRED_X_ID})
#     rec_store_res = (
#         await async_client_bob.get(BASE_PATH + "/credential/store", headers=headers)
#     ).json()
#     assert rec_store_res == ''

# @pytest.mark.asyncio
# async def test_remove_credential(
#     async_client_bob, create_bob_and_alice_connect, create_credential_def
# ):
#     print(CRED_DEF_ID)
#     print(CRED_X_ID)
#     headers = async_client_bob.headers.update({"credential-id": CRED_DEF_ID})
#     x_rec_res = (
#         await async_client_bob.delete(BASE_PATH + "/credential", headers=headers)
#     ).json()
#     assert x_rec_res == ""
