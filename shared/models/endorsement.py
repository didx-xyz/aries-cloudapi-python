from typing import Any, Dict, Literal, Optional

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
    payload: Dict[str, Any]
) -> Optional[str]:
    """Safely extracts the 'type' value from a nested endorsement payload.

    Args:
        payload (Dict[str, Any]): The endorsement event payload.

    Returns:
        Optional[str]: The extracted type value, or None if not found.
    """
    # Attempt to navigate through the nested structure
    messages_attach = payload.get("messages_attach", [])
    if not messages_attach:
        return None  # Early return if 'messages_attach' is empty or does not exist

    for message in messages_attach:
        data = message.get("data")
        if data:
            json_payload = data.get("json")
            if json_payload:
                operation = json_payload.get("operation")
                if operation:
                    operation_type = operation.get("type")
                    if operation_type:
                        return operation_type  # Successfully found the type

    return None  # Return None if the type could not be found
