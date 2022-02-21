from typing import Optional, Union

from aries_cloudcontroller import V10PresentationExchange, V20PresExRecord, IndyProof

from app.generic.verifier.models import (
    IndyProofRequest,
)
from shared_models import PresentationExchange, ProofRequestProtocolVersion


def pres_id_no_version(proof_id: str) -> str:
    if proof_id.startswith("v2-") or proof_id.startswith("v1-"):
        return proof_id[3:]
    else:
        raise ValueError("proof_id must start with prefix v1- or v2-")


def record_to_model(
    record: Union[V20PresExRecord, V10PresentationExchange]
) -> PresentationExchange:
    if isinstance(record, V20PresExRecord):
        return PresentationExchange(
            connection_id=record.connection_id,
            created_at=record.created_at,
            protocol_version=ProofRequestProtocolVersion.v2.value,
            presentation=IndyProof(**record.by_format.pres["indy"])
            if record.by_format.pres
            else None,
            presentation_request=IndyProofRequest(
                **record.by_format.pres_request["indy"]
            ),
            proof_id="v2-" + str(record.pres_ex_id),
            role=record.role,
            state=record.state,
            updated_at=record.updated_at,
            verified=string_to_bool(record.verified),
        )
    elif isinstance(record, V10PresentationExchange):
        return PresentationExchange(
            connection_id=record.connection_id,
            created_at=record.created_at,
            presentation=record.presentation,
            presentation_request=record.presentation_request,
            protocol_version=ProofRequestProtocolVersion.v1.value,
            proof_id="v1-" + str(record.presentation_exchange_id),
            role=record.role,
            state=state_to_rfc_state(record.state),
            updated_at=record.updated_at,
            verified=string_to_bool(record.verified),
        )
    else:
        raise ValueError("Record format unknown.")


def string_to_bool(verified: Optional[str]) -> Optional[bool]:
    if verified == "true":
        return True
    elif verified == "false":
        return False
    else:
        return None


def state_to_rfc_state(state: Optional[str]) -> Optional[str]:
    translation_dict = {
        "proposal_sent": "proposal-sent",
        "proposal_received": "proposal-received",
        "request_sent": "request-sent",
        "request_received": "request-received",
        "presentation_sent": "presentation-sent",
        "presentation_received": "presentation-received",
        "done": "done",
        "abandoned": "abandoned",
    }

    if not state or not state in translation_dict:
        return None

    return translation_dict[state]
