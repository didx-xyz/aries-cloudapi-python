from logging import Logger
from typing import Any, Dict

from shared.constants import GOVERNANCE_LABEL, LAGO_API_KEY, LAGO_URL
from shared.models.endorsement import (
    extract_operation_type_from_endorsement_payload as get_operation_type,
)
from shared.models.endorsement import valid_operation_types


def is_applicable_for_billing(
    wallet_id: str, group_id: str, topic: str, payload: Dict[str, Any], logger: Logger
) -> bool:
    if not LAGO_API_KEY or not LAGO_URL:
        return False  # Only process billable events if Lago is configured

    if wallet_id == GOVERNANCE_LABEL:
        return False

    if not group_id:
        logger.warning("Can't bill for this event as group_id is missing. {} ", payload)
        return False

    state = payload.get("state")
    if topic not in ["proofs", "credentials", "endorsements", "issuer_cred_rev"]:
        logger.debug(
            "Event topic: {} is not applicable for the billing service.", topic
        )
        return False

    if state not in [
        "done",
        "transaction_acked",
        "revoked",
        "credential_acked",
        "presentation_acked",
    ]:
        logger.debug(
            "Event state: {} is not applicable for the billing service.", state
        )
        return False

    if topic == "endorsements":
        operation_type = get_operation_type(payload=payload, logger=logger)
        if operation_type not in valid_operation_types:
            logger.debug(
                "Endorsement operation type: {} is not applicable for the billing service.",
                operation_type,
            )
            return False

    logger.debug("Event is applicable for the billing service.")
    return True
