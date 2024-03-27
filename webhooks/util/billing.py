from logging import Logger
from typing import Any, Dict

from shared.models.endorsement import extract_operation_type_from_endorsement_payload


def is_applicable_for_billing(
    topic: str, payload: Dict[str, Any], logger: Logger
) -> bool:
    state = payload.get("state")
    if topic not in ["proofs", "credentials", "endorsements", "issuer_cred_rev"]:
        logger.debug(f"Event topic: {topic} is not applicable for the billing service.")
        return False

    if state not in [
        "done",
        "transaction_acked",
        "revoked",
        "credential_acked",
        "presentation_acked",
    ]:
        logger.debug(f"Event state: {state} is not applicable for the billing service.")
        return False

    if topic == "endorsements":
        operation_type = get_operation_type(payload=payload, logger=logger)
        if operation_type not in ["1", "100", "102", "113", "114"]:
            logger.debug(
                f"Endorsement operation type: {operation_type} is not applicable for the billing service."
            )
            return False

    logger.debug("Event is applicable for the billing service.")  # info ?
    return True


def get_operation_type(payload: Dict[str, Any], logger: Logger) -> str:

    return extract_operation_type_from_endorsement_payload(
        payload=payload, logger=logger
    )
