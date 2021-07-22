import json
import time
from assertpy import assert_that

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
        name="test_schema", version="0.3", attributes=["speed"]
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
async def test_all(
    async_client_alice,
    async_client_bob,
    create_bob_and_alice_connect,
    create_credential_def,
    yoma_agent_mock,
):
    """
    Bit hacky here. Wrapping the below actual tests into this parent test so they can use the same fixture.
    The agent fixtures create new wallets and new connections between Alice and Bob.
    We only need this done once
    """

    # NOTE To be able to do all variations described here https://github.com/hyperledger/aries-rfcs/blob/master/features/0036-issue-credential/credential-issuance.png
    # We need webhooks
    async def test_issue_credential(
        async_client_bob=async_client_bob,
    ):
        cred_alice = CredentialHelper(
            connection_id=BOB_CONNECTION_ID,
            schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
            credential_attrs=["average"],
        ).json()
        cred_issue_res = (
            await async_client_bob.post(BASE_PATH + "/credential", data=cred_alice)
        ).json()
        global CRED_X_ID
        CRED_X_ID = cred_issue_res["credential"]["credential_exchange_id"]
        assert cred_issue_res["credential"]
        assert cred_issue_res["credential"]["connection_id"] == BOB_CONNECTION_ID
        assert (
            cred_issue_res["credential"]["schema_id"]
            == SCHEMA_DEFINITION_RESULT["schema_id"]
        )

    async def test_offer_credential(
        async_client_bob=async_client_bob,
    ):
        cred_alice = CredentialHelper(
            connection_id=BOB_CONNECTION_ID,
            schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
            credential_attrs=["speed"],
        ).json()
        cred_offer_res = (
            await async_client_bob.post(
                BASE_PATH + "/credential/offer", data=cred_alice
            )
        ).json()
        global CRED_X_ID
        records_b = (await async_client_bob.get(BASE_PATH + "/records")).json()
        print("x-records bob x id: ", records_b["results"][0]["credential_exchange_id"])
        CRED_X_ID = records_b["results"][0]["credential_exchange_id"]
        time.sleep(10)
        assert cred_offer_res["auto_issue"]
        assert cred_offer_res["connection_id"] == BOB_CONNECTION_ID
        assert cred_offer_res["schema_id"] == SCHEMA_DEFINITION_RESULT["schema_id"]

    async def test_get_x_record(async_client_bob=async_client_bob):
        headers = async_client_bob.headers.update({"credential-x-id": CRED_X_ID})
        cred_rec_red = (
            await async_client_bob.get(BASE_PATH + "/credential/", headers=headers)
        ).json()
        assert cred_rec_red["connection_id"] == BOB_CONNECTION_ID
        assert cred_rec_red["schema_id"] == SCHEMA_DEFINITION_RESULT["schema_id"]
        records = await get_records(yoma_agent_mock)
        print("x-records: ", records)

    async def test_get_records(async_client_alice=async_client_alice):
        records = (await async_client_alice.get(BASE_PATH + "/records")).json()
        assert records
        assert records["results"]
        assert len(records["results"]) >= 1

    async def test_send_credential_request(async_client_alice=async_client_bob):
        # TODO check for the successful request
        headers = async_client_alice.headers.update({"credential-x-id": CRED_X_ID})
        time.sleep(10)
        cred_send_res = (
            await async_client_alice.post(
                BASE_PATH + "/credential/request", headers=headers
            )
        ).json()
        # This returns an error - the correct one because the credential is in state received.
        # For this to return another response we'd have to have state offer_received
        assert cred_send_res["error_message"]
        assert "Credential exchange" in cred_send_res["error_message"]

    async def test_store_credential(async_client_bob=async_client_bob):
        # TODO check for the correct response when state is credential_received
        time.sleep(10)
        headers = async_client_bob.headers.update(
            {"credential-x-id": CRED_X_ID, "credential-id": CRED_DEF_ID}
        )
        cred_store_res = (
            await async_client_bob.get(BASE_PATH + "/credential/store", headers=headers)
        ).json()
        time.sleep(10)
        assert cred_store_res["error_message"]
        assert (
            "Credential exchange" and "state (must be credential_received)."
        ) in cred_store_res["error_message"]

    async def test_send_proposal(async_client_alice=async_client_alice):
        # TODO check for the correct response when state is credential_received
        cred_alice = CredentialHelper(
            connection_id=ALICE_CONNECTION_ID,
            schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
            credential_attrs=["average"],
        ).json()
        prop_prop_res = (
            await async_client_alice.post(
                BASE_PATH + "/credential/proposal", data=cred_alice
            )
        ).json()
        assert prop_prop_res["auto_issue"] is False
        assert prop_prop_res["auto_remove"]
        assert prop_prop_res["connection_id"] == ALICE_CONNECTION_ID

    async def test_send_problem_report(async_client_bob=async_client_bob):
        # TODO check for the correct response when state is credential_received
        async_client_bob.headers.update({"credential-x-id": CRED_X_ID})
        cred_store_res = (
            await async_client_bob.post(
                BASE_PATH + "/problem-report",
                data=json.dumps({"explanation": "Problem"}),
            )
        ).json()
        # This is the best we can do for now until we turn auto respond off
        # or have webhooks listeners
        assert cred_store_res

    # NOTE it si with the current fastapi state not possible to test all scenarios
    # described here: https://github.com/hyperledger/aries-rfcs/blob/master/features/0036-issue-credential/credential-issuance.png
    # This also has to do with the AUTO_RESPOND_* startup args aca-py
    # We need webhooks to handle the exchange states
    await test_issue_credential()
    await test_send_proposal()
    await test_get_x_record()
    await test_offer_credential()
    await test_send_credential_request()
    await test_send_problem_report()
    await test_store_credential()
    await test_get_records()
