import json
import time
import pytest
from generic.issuer_v2 import (
    Credential,
    CredentialOffer,
)
from tests.utils_test import get_random_string
from admin.governance.credential_definitions import (
    CredentialDefinition,
    create_credential_definition,
    get_credential_definition,
)
from tests.admin.governance.schemas.test_schemas import create_public_did
from admin.governance.schemas import SchemaDefinition, create_schema

APPLICATION_JSON_CONTENT_TYPE = {"content-type": "application/json"}
ALICE_CONNECTION_ID = ""
BOB_CONNECTION_ID = ""
BASE_PATH = "/generic/connections"
ISSUER_PATH = "/generic/issuers/v2"
ISSUER_HEADERS = {
    "content-type": "application/json",
    "x-role": "yoma",
    "x-api-key": "adminApiKey",
}
SCHEMA_DEFINITION_RESULT = {}
CRED_DEF_ID = ""
CRED_X_ID = ""


@pytest.fixture
@pytest.mark.asyncio
async def test_bob_and_alice_connect(async_client_bob, async_client_alice):
    """this test validates that bob and alice connect successfully...
    NB: it assumes you have all the "auto connection" settings flagged as on.
    ACAPY_AUTO_ACCEPT_INVITES=true
    ACAPY_AUTO_ACCEPT_REQUESTS=true
    ACAPY_AUTO_PING_CONNECTION=true
    """
    # create invitation on bob side
    invitation = (await async_client_bob.get(BASE_PATH + "/create-invite")).json()
    bob_connection_id = invitation["connection_id"]
    connections = (await async_client_bob.get(BASE_PATH)).json()

    # accept invitation on alice side
    invite_response = (
        await async_client_alice.post(
            BASE_PATH + "/accept-invite", data=json.dumps(invitation["invitation"])
        )
    ).json()
    alice_connection_id = invite_response["connection_id"]

    # wait for events to be exchanged
    time.sleep(10)

    # fetch and validate
    # both connections should be active - we have waited long enough for events to be exchanged
    # and we are running in "auto connect" mode.
    bob_connections = (await async_client_bob.get(BASE_PATH)).json()
    alice_connections = (await async_client_alice.get(BASE_PATH)).json()
    bob_connection = [
        c for c in bob_connections["results"] if c["connection_id"] == bob_connection_id
    ][0]
    alice_connection = [
        c
        for c in alice_connections["results"]
        if c["connection_id"] == alice_connection_id
    ][0]

    global ALICE_CONNECTION_ID, BOB_CONNECTION_ID
    ALICE_CONNECTION_ID = alice_connection_id
    BOB_CONNECTION_ID = bob_connection_id
    return ALICE_CONNECTION_ID, BOB_CONNECTION_ID


@pytest.fixture
@pytest.mark.asyncio
async def test_create_credential_def(yoma_agent_mock):
    definition = SchemaDefinition(
        name="test_schema", version="0.3", attributes=["speed"]
    )

    public_did = await create_public_did(yoma_agent_mock)
    print(f" created did:{public_did}")
    schema_definition_result = (await create_schema(definition, yoma_agent_mock)).dict()
    print(schema_definition_result)
    credential_definition = CredentialDefinition(
        schema_id=schema_definition_result["schema_id"],
        tag=get_random_string(5),
        support_revocation=False,
    )

    # when
    result = (
        await create_credential_definition(credential_definition, yoma_agent_mock)
    ).dict()

    # then
    written = (
        await get_credential_definition(
            result["credential_definition_id"], yoma_agent_mock
        )
    ).dict()
    global CRED_DEF_ID
    CRED_DEF_ID = written["credential_definition"]["id"]
    global SCHEMA_DEFINITION_RESULT
    SCHEMA_DEFINITION_RESULT = schema_definition_result
    return credential_definition


@pytest.mark.asyncio
async def test_all(
    async_client,
    async_client_alice,
    async_client_bob,
    test_bob_and_alice_connect,
    test_create_credential_def,
    yoma_agent_mock,
):
    async def test_send_credential(
        async_client_alice=async_client_alice,
    ):
        cred_alice = Credential(
            connection_id=ALICE_CONNECTION_ID,
            schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
            cred_def_id=CRED_DEF_ID,
            attributes=["average"],
        ).json()
        cred_send_res = (
            await async_client_alice.post(ISSUER_PATH + "/credential", data=cred_alice)
        ).json()
        global CRED_X_ID
        CRED_X_ID = cred_send_res["cred_ex_id"]
        if cred_send_res and "conn_id" in cred_send_res.keys():
            assert cred_send_res["conn_id"] == ALICE_CONNECTION_ID
        else:
            assert cred_send_res["connection_id"] == ALICE_CONNECTION_ID

    async def test_offer_credential(
        async_client_alice=async_client_alice,
    ):
        cred_alice = CredentialOffer(
            connection_id=ALICE_CONNECTION_ID,
            schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
            cred_def_id=CRED_DEF_ID,
            attributes=["speed"],
        ).json()
        cred_offer_res = (
            await async_client_alice.post(
                ISSUER_PATH + "/credential/offer", data=cred_alice
            )
        ).json()
        assert cred_offer_res["auto_issue"]
        assert cred_offer_res["connection_id"] == ALICE_CONNECTION_ID
        assert (
            cred_offer_res["by_format"]["cred_offer"]["indy"]["schema_id"]
            == SCHEMA_DEFINITION_RESULT["schema_id"]
        )
        assert cred_offer_res["cred_ex_id"]

    async def test_get_records(async_client_alice=async_client_alice):
        time.sleep(5)
        async_client_alice.headers.update({"connection-id": ALICE_CONNECTION_ID})
        records = (
            await async_client_alice.get(
                ISSUER_PATH + "/records",
            )
        ).json()
        assert records

    # TODO Fix this test - method return "Record ID not provided." alhtough record id is not inrequired schemas
    # See also https://github.com/didx-xyz/aries-cloudcontroller-python/issues/62
    # async def test_send_credential_proposal(async_client_alice=async_client_alice):
    #     cred_alice = Proposal(
    #         connection_id=ALICE_CONNECTION_ID,
    #         schema_id=SCHEMA_DEFINITION_RESULT["schema_id"],
    #         attributes=["avg"],
    #     ).json()
    #     prop_send_response = (
    #         await async_client_alice.post(
    #             ISSUER_PATH + "/credential/proposal", data=cred_alice
    #         )
    #     ).json()
    #     assert prop_send_response["auto_issue"] == False
    #     assert prop_send_response["auto_remove"]
    #     if "conn_id" in prop_send_response.keys():
    #         assert prop_send_response["conn_id"] == ALICE_CONNECTION_ID
    #     else:
    #         assert prop_send_response["connection_id"] == ALICE_CONNECTION_ID

    async def test_credential_request(async_client_alice=async_client_alice):
        headers = async_client_alice.headers.update({"credential-x-id": CRED_X_ID})
        cred_send_response = (
            await async_client_alice.post(
                ISSUER_PATH + "/credential/request", headers=headers
            )
        ).json()
        assert cred_send_response["error_message"]
        assert "credential exchange" in cred_send_response["error_message"]

    async def test_send_problem_report(async_client_alice=async_client_alice):
        cred_store_res = (
            await async_client_alice.post(
                ISSUER_PATH + f"/problem-report?credential_x_id={CRED_X_ID}",
                data=json.dumps({"description": "Problem"}),
            )
        ).json()
        assert cred_store_res == {}

    await test_send_credential()
    # await test_send_credential_proposal()

    await test_offer_credential()
    await test_get_records()

    await test_credential_request()
    await test_send_problem_report()
