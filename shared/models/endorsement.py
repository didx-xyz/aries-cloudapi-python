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
        return None  # Early return if 'messages_attach' is empty or does not exist

    try:
        for message in messages_attach:
            data = message.get("data")
            if data:
                json_payload = data.get("json")
                if json_payload:
                    json_parsed = orjson.loads(json_payload)
                    operation = json_parsed.get("operation")
                    if operation:
                        operation_type = operation.get("type")
                        if operation_type:
                            return operation_type  # Successfully found the type
    except Exception as e:
        logger.warning(
            f"Exception while extracting operation type from endorsement payload. {e}.\nContinuing..."
        )

    return None  # Return None if the type could not be found or if error occurred


def is_applicable_for_endorser(payload: Dict[str, Any], logger: Logger) -> bool:
    operation_type = extract_operation_type_from_endorsement_payload(payload, logger)
    return operation_type == "102"
