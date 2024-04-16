from logging import Logger
from typing import Any, Dict, Optional, Tuple

from shared.constants import GOVERNANCE_LABEL, LAGO_API_KEY, LAGO_URL
from shared.models.endorsement import (
    extract_operation_type_from_endorsement_payload as get_operation_type,
)
from shared.models.endorsement import valid_operation_types


def is_applicable_for_billing(
    wallet_id: str, group_id: str, topic: str, payload: Dict[str, Any], logger: Logger
) -> Tuple[bool, Optional[str]]:
    if not LAGO_API_KEY or not LAGO_URL:
        return False, None  # Only process billable events if Lago is configured

    if wallet_id == GOVERNANCE_LABEL:
        return False, None

    if not group_id:
        logger.warning("Can't bill for this event as group_id is missing: {}", payload)
        return False, None

    if topic not in ["proofs", "credentials", "endorsements", "issuer_cred_rev"]:
        logger.debug("Event topic {} is not applicable for the billing service.", topic)
        return False, None

    state = payload.get("state")
    if state not in [
        "done",
        "transaction_acked",
        "revoked",
        "credential_acked",
        "presentation_acked",  # For proofs holder done v1
        "verified",  # For proofs verifier done v1
    ]:
        logger.debug("Event state {} is not applicable for the billing service.", state)
        return False, None

    operation_type = None
    if topic == "endorsements":
        operation_type = get_operation_type(payload=payload, logger=logger)
        if operation_type not in valid_operation_types:
            logger.debug(
                "Endorsement operation type {} is not applicable for billing.",
                operation_type,
            )
            return False, None

    if topic == "proofs":
        role = payload.get("role")
        if role != "verifier":
            logger.debug("Proof role {} is not applicable for billing.", role)
            return False, None

    logger.debug("Event is applicable for the billing service.")
    return True, operation_type
