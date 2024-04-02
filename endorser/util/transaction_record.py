import json
from typing import Any, Dict, Optional

from aries_cloudcontroller import AcaPyClient, TransactionRecord

from shared.log_config import get_logger
from shared.models.endorsement import TransactionTypes

logger = get_logger(__name__)


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
                "Attachment does not contain expected key `data`. Got attachment: `{}`.",
                attachment,
            )
            return None

        if not isinstance(attachment["data"], dict) or "json" not in attachment["data"]:
            logger.debug(
                "Attachment data does not contain expected keys `json`. Got attachment data: `{}`.",
                attachment["data"],
            )
            return None

        json_payload = attachment["data"]["json"]

        # Both dict and str encoding have occurred for the attachment data
        # Parse to dict if payload is of type str
        if isinstance(json_payload, str):
            logger.debug("Try cast attachment payload to json")
            try:
                json_payload = json.loads(json_payload)
                logger.debug("Payload is valid JSON.")
            except json.JSONDecodeError:
                logger.warning("Failed to decode attachment payload. Invalid JSON.")
                json_payload = None

        return json_payload
    except (TypeError, KeyError):
        logger.warning("Could not read attachment from transaction: `{}`.", transaction)
    except Exception:
        logger.exception(
            "Exception caught while running `get_endorsement_request_attachment`."
        )
    return None


def is_credential_definition_transaction(operation_type: str) -> bool:
    # credential definition type is 102
    # see https://github.com/hyperledger/indy-node/blob/master/docs/source/requests.md#common-request-structure
    return operation_type == TransactionTypes.CLAIM_DEF


async def get_did_and_schema_id_from_cred_def_attachment(
    client: AcaPyClient, attachment: Dict[str, Any]
):
    if "identifier" not in attachment:
        logger.warning(
            "Expected key `identifier` does not exist in extracted attachment. Got attachment: `{}`.",
            attachment,
        )
        return False

    # `operation` key is asserted to exist in `is_credential_definition_transaction`
    if "ref" not in attachment["operation"]:
        logger.warning(
            "Expected key `ref` does not exist in attachment `operation`. Got operation: `{}`.",
            attachment["operation"],
        )
        return False

    did = "did:sov:" + attachment["identifier"]
    schema_seq_id = attachment["operation"]["ref"]

    logger.debug("Fetching schema with seq id: `{}`", schema_seq_id)
    schema = await client.schema.get_schema(schema_id=str(schema_seq_id))

    if not schema.var_schema or not schema.var_schema.id:
        raise Exception("Could not extract schema id from schema response.")

    schema_id = schema.var_schema.id

    return (did, schema_id)


def is_attrib_type(operation_type: str) -> bool:
    return operation_type == TransactionTypes.ATTRIB


def is_revocation_def_or_entry(operation_type: str) -> bool:
    return operation_type in [
        TransactionTypes.REVOC_REG_DEF,
        TransactionTypes.REVOC_REG_ENTRY,
    ]
