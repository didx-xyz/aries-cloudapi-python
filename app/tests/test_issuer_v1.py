import asyncio
import json
import time
from assertpy import assert_that

import acapy_ledger_facade
from admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_credential_definition,
)
from admin.governance.schemas import SchemaDefinition, create_schema
from tests.admin.governance.schemas.test_schemas import create_public_did
from tests.utils_test import get_random_string

import pytest
from generic.issuers_v1 import (
    CredentialHelper,
)
from aries_cloudcontroller import CredentialProposal

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
BASE_PATH = "/generic/issuers/v1"
BASE_PATH_CON = "/generic/connections"
CRED_X_ID = ""
CRED_DEF_ID = ""


@pytest.yield_fixture(scope="module")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
@pytest.mark.asyncio
async def create_bob_and_alice_connect(
    async_client_bob_module_scope, async_client_alice_module_scope
):
    async_client_bob = async_client_bob_module_scope
    async_client_alice = async_client_alice_module_scope
    """This test validates that bob and alice connect successfully...

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
    time.sleep(15)
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

    return {
        "alice_connection_id": alice_connection_id,
        "bob_connection_id": bob_connection_id,
    }


@pytest.fixture(scope="module")
def bob_connection_id(create_bob_and_alice_connect):
    return create_bob_and_alice_connect["bob_connection_id"]


@pytest.fixture(scope="module")
def alice_connection_id(create_bob_and_alice_connect):
    return create_bob_and_alice_connect["alice_connection_id"]


@pytest.fixture(scope="module")
async def schema_definition(yoma_agent_module_scope):
    definition = SchemaDefinition(
        name="test_schema", version="0.3", attributes=["speed"]
    )

    public_did = await acapy_ledger_facade.create_pub_did(yoma_agent_module_scope)
    print(f"created did: {public_did}")
    schema_definition_result = await create_schema(definition, yoma_agent_module_scope)
    print(schema_definition_result)

    print(f"created schema {str(schema_definition_result)}")
    return (schema_definition_result).dict()


@pytest.fixture(scope="module")
async def credential_definition(yoma_agent_module_scope, schema_definition):

    credential_definition = CredentialDefinition(
        schema_id=schema_definition["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = await create_credential_definition(
        credential_definition, yoma_agent_module_scope
    )
    result = result.dict()

    # then
    written = await get_credential_definition(
        result["credential_definition_id"], yoma_agent_module_scope
    )
    global CRED_DEF_ID
    CRED_DEF_ID = result["credential_definition_id"]
    print(f"created definition {str(result)}")
    return result

    # NOTE To be able to do all variations described here https://github.com/hyperledger/aries-rfcs/blob/master/features/0036-issue-credential/credential-issuance.png
    # We need webhooks


@pytest.mark.asyncio
async def test_issue_credential(
    async_client_bob_module_scope,
    schema_definition,
    bob_connection_id,
    async_client_alice_module_scope,
):
    cred_alice = CredentialHelper(
        connection_id=bob_connection_id,
        schema_id=schema_definition["schema_id"],
        credential_attrs=["average"],
    ).json()
    records = await async_client_alice_module_scope.get(BASE_PATH + "/records")
    assert not records.json()["results"]  # nothing currently in alices records
    cred_issue_res = (
        await async_client_bob_module_scope.post(
            BASE_PATH + "/credential", data=cred_alice
        )
    ).json()
    global CRED_X_ID
    CRED_X_ID = cred_issue_res["credential_exchange_id"]
    assert cred_issue_res["credential_offer"]
    assert cred_issue_res["connection_id"] == bob_connection_id
    assert (
        cred_issue_res["credential_offer"]["schema_id"]
        == schema_definition["schema_id"]
    )

    time.sleep(5)
    records = await async_client_alice_module_scope.get(BASE_PATH + "/records")
    print(str(records.json()))
    # after credential issued, alice has something
    assert records.json()["results"]


@pytest.fixture(scope="module")
async def credential_exchange_id(
    async_client_bob_module_scope,
    schema_definition,
    bob_connection_id,
    async_client_alice_module_scope,
):
    """this fixture produces the CRED_X_ID but if the test that produces the CRED_X_ID has already run
    then this fixture just returns it..."""
    global CRED_X_ID
    if CRED_X_ID:
        return CRED_X_ID

    cred_alice = CredentialHelper(
        connection_id=bob_connection_id,
        schema_id=schema_definition["schema_id"],
        credential_attrs=["average"],
    ).json()
    records = await async_client_alice_module_scope.get(BASE_PATH + "/records")
    assert not records.json()["results"]  # nothing currently in alices records
    cred_issue_res = (
        await async_client_bob_module_scope.post(
            BASE_PATH + "/credential", data=cred_alice
        )
    ).json()
    CRED_X_ID = cred_issue_res["credential"]["credential_exchange_id"]
    assert cred_issue_res["credential"]
    assert cred_issue_res["credential"]["connection_id"] == bob_connection_id
    assert cred_issue_res["credential"]["schema_id"] == schema_definition["schema_id"]

    time.sleep(5)
    records = await async_client_alice_module_scope.get(BASE_PATH + "/records")
    print(str(records.json()))
    # after credential issued, alice has something
    assert records.json()["results"]
    return CRED_X_ID


# TODO: Fix this test - unprocessible entity for cred_offer_res
# @pytest.mark.asyncio
# async def test_offer_credential(
#     async_client_bob_module_scope, schema_definition, bob_connection_id
# ):
#     async_client_bob = async_client_bob_module_scope
#     cred_alice = CredentialProposal(
#         cred_def_id == CRED_DEF_ID,
#         schema_id=schema_definition["schema_id"],
#     ).json()
#     cred_offer_res = (
#         await async_client_bob.post(
#             BASE_PATH + "/credential/offer?cred_ex_id={CRED_EX_ID}", data=cred_alice
#         )
#     ).json()
#     global CRED_X_ID
#     records_b = (await async_client_bob.get(BASE_PATH + "/records")).json()
#     print("x-records bob x id: ", records_b["results"][0]["credential_exchange_id"])
#     CRED_X_ID = records_b["results"][0]["credential_exchange_id"]
#     time.sleep(10)
#     assert cred_offer_res == ""
#     assert cred_offer_res["credential"]["auto_issue"]
#     assert cred_offer_res["credential"]["connection_id"] == bob_connection_id
#     assert cred_offer_res["credential"]["schema_id"] == schema_definition["schema_id"]


@pytest.mark.asyncio
async def test_get_x_record(
    async_client_bob_module_scope,
    bob_connection_id,
    credential_exchange_id,
    schema_definition,
):
    cred_rec_red = (
        await async_client_bob_module_scope.get(
            BASE_PATH + f"/credential?credential_x_id={credential_exchange_id}"
        )
    ).json()
    assert cred_rec_red["connection_id"] == bob_connection_id
    assert cred_rec_red["schema_id"] == schema_definition["schema_id"]


@pytest.mark.asyncio
async def test_get_records(async_client_alice_module_scope):
    records = (await async_client_alice_module_scope.get(BASE_PATH + "/records")).json()
    assert records
    assert records["results"]
    assert len(records["results"]) >= 1


@pytest.mark.asyncio
async def test_send_credential_request(async_client_bob_module_scope):
    # TODO check for the successful request
    time.sleep(10)
    cred_send_res = (
        await async_client_bob_module_scope.post(
            BASE_PATH + f"/credential/request?credential_x_id={CRED_X_ID}"
        )
    ).json()
    # This returns an error - the correct one because the credential is in state received.
    # For this to return another response we'd have to have state offer_received
    assert cred_send_res["error_message"]
    assert "Credential exchange" in cred_send_res["error_message"]


@pytest.mark.asyncio
async def test_store_credential(async_client_bob_module_scope, credential_definition):
    # TODO check for the correct response when state is credential_received
    time.sleep(5)
    cred_store_res = (
        await async_client_bob_module_scope.get(
            BASE_PATH
            + f"/credential/store?credential_x_id={CRED_X_ID}&credential_id={CRED_DEF_ID}"
        )
    ).json()
    time.sleep(5)
    assert cred_store_res["error_message"]
    assert (
        "Credential exchange" and "state (must be credential_received)."
    ) in cred_store_res["error_message"]


@pytest.mark.asyncio
async def test_send_proposal(
    async_client_alice_module_scope, alice_connection_id, schema_definition
):
    # TODO check for the correct response when state is credential_received
    cred_alice = CredentialHelper(
        connection_id=alice_connection_id,
        schema_id=schema_definition["schema_id"],
        credential_attrs=["average"],
    ).json()
    prop_prop_res = (
        await async_client_alice_module_scope.post(
            BASE_PATH + "/credential/proposal", data=cred_alice
        )
    ).json()
    assert prop_prop_res["auto_issue"] is False
    assert prop_prop_res["auto_remove"] is False
    assert prop_prop_res["connection_id"] == alice_connection_id


@pytest.mark.asyncio
async def test_send_problem_report(async_client_bob_module_scope):
    # TODO check for the correct response when state is credential_received
    cred_store_res = (
        await async_client_bob_module_scope.post(
            BASE_PATH + f"/problem-report?credential_x_id={CRED_X_ID}",
            data=json.dumps({"description": "Problem"}),
        )
    ).json()
    # This is the best we can do for now until we turn auto respond off
    # or have webhooks listeners
    assert cred_store_res == {}
