import json
from typing import Any, Dict, Optional, TypedDict

import httpx
from aries_cloudcontroller import AcaPyClient, TransactionRecord
from aries_cloudcontroller.util.acapy_client_session import AcaPyClientSession
from fastapi_websocket_pubsub import PubSubClient

from endorser.config.log_config import get_logger
from shared import (
    GOVERNANCE_AGENT_API_KEY,
    GOVERNANCE_AGENT_URL,
    TRUST_REGISTRY_URL,
    WEBHOOKS_PUBSUB_URL,
    Endorsement,
)

logger = get_logger(__name__)


class Event(TypedDict):
    payload: Dict[str, Any]
    origin: str
    wallet_id: str


async def listen_endorsement_events():
    topic = "endorsements-admin"

    client = PubSubClient([topic], callback=process_endorsement_event)
    logger.debug("Opening connection to webhook server")
    client.start_client(WEBHOOKS_PUBSUB_URL)
    logger.debug("Opened connection to webhook server. waiting for readiness...")
    await client.wait_until_done()
    logger.debug("Connection to webhook server ready")
    logger.info(
        "Listening for 'endorsements' events from webhook server at {}",
        WEBHOOKS_PUBSUB_URL,
    )


# topic is unused, but passed by the fastapi library.
async def process_endorsement_event(data: str, topic: str):
    event: Event = json.loads(data)
    logger.debug(
        "Processing endorsement event for agent {}, wallet: {}",
        event["origin"],
        event["wallet_id"],
    )
    # We're only interested in events from the governance agent
    if not is_governance_agent(event):
        logger.debug("Endorsement request is not for governance agent.")
        return

    endorsement = Endorsement(**event["payload"])

    async with AcaPyClient(
        base_url=GOVERNANCE_AGENT_URL, api_key=GOVERNANCE_AGENT_API_KEY
    ) as client:
        # Not interested in this endorsement request
        if not await should_accept_endorsement(client, endorsement):
            logger.debug(
                "Endorsement request with transaction id {} is not applicable for endorsement.",
                endorsement.transaction_id,
            )
            return

        logger.debug(
            "Endorsement request with transaction id {} is applicable for endorsement, accepting request.",
            endorsement.transaction_id,
        )
        await accept_endorsement(client, endorsement)


def is_governance_agent(event: Event):
    return event["origin"] == "governance"


async def should_accept_endorsement(
    client: AcaPyClient, endorsement: Endorsement
) -> bool:
    """Check whether a transaction endorsement request should be endorsed.

    Whether the request should be accepted is based on the follow criteria:
    1. The transaction is for a credential definition
    2. The did is registered as an issuer in the trust registry.
    3. The schema_id is registered in the trust registry.

    Args:
        endorsement (Endorsement): The endorsement event model

    Returns:
        bool: Whether the endorsement request should be accepted
    """
    bound_logger = logger.bind(body=endorsement)
    bound_logger.debug("Validating if endorsement transaction should be endorsed")

    transaction_id = endorsement.transaction_id
    bound_logger.debug("Fetching transaction with id: {}", transaction_id)
    transaction = await client.endorse_transaction.get_transaction(
        tran_id=transaction_id
    )

    if transaction.state != "request_received":
        bound_logger.debug(
            "Endorsement event for transaction with id '{}' "
            "not in state 'request_received' (is '{}').",
            transaction_id,
            transaction.state,
        )
        return False

    attachment = get_endorsement_request_attachment(transaction)

    if not attachment:
        bound_logger.debug("Could not extract attachment from transaction.")
        return False

    if not is_credential_definition_transaction(attachment):
        bound_logger.debug("Endorsement request is not for credential definition.")
        return False

    if "identifier" not in attachment:
        bound_logger.debug(
            "Expected key `identifier` does not exist in extracted attachment. Got attachment: {}.",
            attachment,
        )
        return False

    # `operation` key is asserted to exist in `is_credential_definition_transaction`
    if "ref" not in attachment["operation"].keys():
        bound_logger.debug(
            "Expected key `ref` does not exist in attachment `operation`. Got operation: {}",
            attachment["operation"],
        )
        return False

    did, schema_id = await get_did_and_schema_id_from_cred_def_attachment(
        client, attachment
    )

    if not await is_valid_issuer(did, schema_id):
        bound_logger.debug(
            "Endorsement request with transaction id {} is not for did "
            "and schema registered in the trust registry.",
            transaction_id,
        )
        return False

    return True


async def get_did_and_schema_id_from_cred_def_attachment(
    client: AcaPyClient, attachment: Dict[str, Any]
):
    did = "did:sov:" + attachment["identifier"]
    schema_seq_id = attachment["operation"]["ref"]

    logger.debug("Fetching schema with seq id: {}", schema_seq_id)
    schema = await client.schema.get_schema(schema_id=schema_seq_id)

    if not schema.schema_ or not schema.schema_.id:
        raise Exception("Could not extract schema id from schema response")

    schema_id = schema.schema_.id

    return (did, schema_id)


def get_endorsement_request_attachment(
    transaction: TransactionRecord,
) -> Optional[Dict[str, Any]]:
    try:
        if not transaction.messages_attach:
            logger.debug("No message attachments in transaction")
            return None

        attachment: Dict = transaction.messages_attach[0]

        if "data" not in attachment:
            logger.debug(
                "Attachment does not contain expected key `data`. Got attachment: {}",
                attachment,
            )
            return None

        if (
            not isinstance(attachment["data"], Dict)
            or "json" not in attachment["data"].keys()
        ):
            logger.debug(
                "Attachment data does not contain expected keys `json`. Got attachment data: {}",
                attachment["data"],
            )
            return None

        json_payload = attachment["data"]["json"]

        # Both dict and str encoding have ocurred for the attachment data
        # Parse to dict if payload is of type str
        if isinstance(json_payload, str):
            logger.debug("Obtained string from `.data.json`; cast to json payload")
            json_payload = json.loads(json_payload)

        return json_payload
    except Exception:
        logger.exception(
            "Exception caught while running `get_endorsement_request_attachment`."
        )
        return None


def is_credential_definition_transaction(attachment: Dict[str, Any]) -> bool:
    try:
        if "operation" not in attachment:
            logger.debug("Key `operation` not in attachment: {}.", attachment)
            return False

        operation = attachment["operation"]

        if "type" not in operation:
            logger.debug("Key `type` not in operation attachment.")
            return False

        logger.debug(
            "Endorsement request operation type: %s. Need 102", operation.get("type")
        )

        # credential definition type is 102
        # see https://github.com/hyperledger/indy-node/blob/master/docs/source/requests.md#common-request-structure
        return operation.get("type") == "102"
    except Exception:
        logger.exception(
            "Exception caught while running `is_credential_definition_transaction`."
        )
        return False


async def is_valid_issuer(did: str, schema_id: str):
    """Assert that an actor with the specified did is registered as issuer.

    This method asserts that there is an actor registered in the trust registry
    with the specified did. It verifies whether this actor has the `issuer` role
    and will also make sure the specified schema_id is registered as a valid schema.
    Raises an exception if one of the assertions fail.

    NOTE: the dids in the registry are registered as fully qualified dids. This means
    when passing a did to this method it must also be fully qualified (e.g. `did:sov:xxxx`)

    Args:
        did (str): the did of the issuer in fully qualified format.
        schema_id (str): the schema_id of the credential being issued

    Raises:
        Exception: When the did is not registered, the actor doesn't have the issuer role
            or the schema is not registered in the registry.
    """
    bound_logger = logger.bind(body={"did": did, "schema_id": schema_id})
    bound_logger.debug("Assert that did is registered as issuer")
    try:
        async with httpx.AsyncClient() as client:
            bound_logger.debug("Fetch actor with did {} from trust registry", did)
            actor_res = await client.get(
                f"{TRUST_REGISTRY_URL}/registry/actors/did/{did}"
            )
    except httpx.HTTPError as e:
        bound_logger.exception(
            "Caught HTTP error when reading actor from trust registry."
        )
        raise e from e

    if actor_res.is_error:
        bound_logger.error(
            "Error retrieving actor for did {} from trust registry. {}",
            did,
            actor_res.text,
        )
        return False
    actor = actor_res.json()

    # We need role issuer
    if "roles" not in actor or "issuer" not in actor["roles"]:
        bound_logger.error("Actor {} does not have required role 'issuer'", actor)
        return False

    try:
        async with httpx.AsyncClient() as client:
            bound_logger.debug("Fetch schemas from trust registry")
            schema_res = await client.get(f"{TRUST_REGISTRY_URL}/registry/schemas")
    except httpx.HTTPError as e:
        raise e from e

    if schema_res.is_error:
        logger.error(
            "Error retrieving schemas from trust registry. {}", schema_res.text
        )
        return False

    schemas = schema_res.json()["schemas"]
    if schema_id not in schemas:
        logger.info("Schema {} not in the trust registry.", schema_id)
        return False

    bound_logger.debug("Validated that DID and schema are on trust registry")
    return True


async def accept_endorsement(client: AcaPyClient, endorsement: Endorsement):
    logger.debug("Endorsing transaction with id: {}", endorsement.transaction_id)
    await client.endorse_transaction.endorse_transaction(
        tran_id=endorsement.transaction_id
    )
