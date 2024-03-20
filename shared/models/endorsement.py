from logging import Logger
from typing import Any, Dict, Literal, Optional

import orjson
from pydantic import BaseModel


class Endorsement(BaseModel):
    state: Literal[
        "request-received",
        "request-sent",
        "transaction-acked",
        "transaction-cancelled",
        "transaction-created",
        "transaction-endorsed",
        "transaction-refused",
        "transaction-resent",
        "transaction-resent_received",
    ]
    transaction_id: str


def extract_operation_type_from_endorsement_payload(
    payload: Dict[str, Any], logger: Logger
) -> Optional[str]:
    """Safely extracts the 'type' value from a nested endorsement payload.

    Args:
        payload (Dict[str, Any]): The endorsement event payload.
        logger (Logger): A logging object, of course.

    Returns:
        Optional[str]: The extracted type value, or None if not found.
    """
    # Attempt to navigate through the nested structure
    messages_attach = payload.get("messages_attach", [])
    if not messages_attach:
        logger.debug("No `messages_attach` found in endorsement payload.")
        return None  # Early return if 'messages_attach' is empty or does not exist

    try:
        for message in messages_attach:
            data = message.get("data")
            if data:
                json_payload = data.get("json")
                if json_payload:
                    if isinstance(json_payload, str):
                        json_dict = orjson.loads(json_payload)
                    elif isinstance(json_payload, dict):
                        json_dict = json_payload
                    else:
                        logger.warning("Unexpected json payload: {}", json_payload)
                        return None

                    operation = json_dict.get("operation")
                    if operation:
                        operation_type = operation.get("type")
                        if operation_type:
                            return operation_type  # Successfully found the type
    except orjson.JSONDecodeError as e:
        logger.warning(
            "Couldn't extract json payload from {}. {}. Continuing...", json_payload, e
        )
    except Exception as e:
        logger.warning(
            "Exception while extracting operation type from endorsement payload. {}. Continuing...",
            e,
        )

    return None  # Return None if the type could not be found or if error occurred


class TransactionTypes:
    # See aries-cloudagent-python/aries_cloudagent/ledger/merkel_validation/constants.py
    ATTRIB = "100"
    CLAIM_DEF = "102"
    REVOC_REG_DEF = "113"
    REVOC_REG_ENTRY = "114"


applicable_transaction_state = "request_received"

valid_operation_types = [
    TransactionTypes.ATTRIB,
    TransactionTypes.CLAIM_DEF,
    TransactionTypes.REVOC_REG_DEF,
    TransactionTypes.REVOC_REG_ENTRY,
]


def payload_is_applicable_for_endorser(payload: Dict[str, Any], logger: Logger) -> bool:
    state = payload.get("state")

    if state == applicable_transaction_state:
        logger.debug("Endorsement payload in eligible state: {}", state)
    else:
        logger.debug("Endorsement payload not in eligible state: {}", state)
        return False

    operation_type = extract_operation_type_from_endorsement_payload(payload, logger)

    if not operation_type:
        logger.debug("Could not extract an operation type from payload.")
        return False

    is_applicable = operation_type in valid_operation_types
    if is_applicable:
        logger.debug("Endorsement payload is applicable for the endorser service.")
    else:
        logger.debug(
            "Endorsement payload is not applicable for the endorser service, with operation type {}.",
            operation_type,
        )
    return is_applicable
