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
        logger.info("No `messages_attach` found in endorsement payload.")
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
                        logger.warning(f"Unexpected json payload: {json_payload}")
                        return None

                    operation = json_dict.get("operation")
                    if operation:
                        operation_type = operation.get("type")
                        if operation_type:
                            return operation_type  # Successfully found the type
    except orjson.JSONDecodeError as e:
        logger.info(
            f"Couldn't extract json payload from {json_payload}. {e}. Continuing..."
        )
    except Exception as e:
        logger.warning(
            f"Exception while extracting operation type from endorsement payload. {e}. Continuing..."
        )

    return None  # Return None if the type could not be found or if error occurred


def payload_is_applicable_for_endorser(payload: Dict[str, Any], logger: Logger) -> bool:
    state = payload.get("state")

    if state == "request_received":
        logger.info("Endorsement payload in eligible state: {}", state)
    else:
        logger.info("Endorsement payload not in eligible state: {}", state)
        return False

    operation_type = extract_operation_type_from_endorsement_payload(payload, logger)

    if not operation_type:
        logger.info("Could not extract an operation type from payload.")
        return False

    is_applicable = operation_type == "102"
    if is_applicable:
        logger.info("Endorsement payload is applicable for the endorser service.")
    else:
        logger.info(
            "Endorsement payload is not applicable for the endorser service, with operation type {}.",
            operation_type,
        )
    return is_applicable
