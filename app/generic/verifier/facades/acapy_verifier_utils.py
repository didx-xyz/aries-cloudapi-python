import logging
from enum import Enum
from typing import List, Optional, Set, Union

from aries_cloudcontroller import AcaPyClient, ConnRecord, IndyPresSpec

from app.exceptions.cloud_api_error import CloudApiException
from app.facades.acapy_wallet import assert_public_did
from app.facades.trust_registry import Actor, actor_by_did, get_trust_registry_schemas
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.generic.verifier.facades.acapy_verifier_v1 import VerifierV1
from app.generic.verifier.facades.acapy_verifier_v2 import VerifierV2
from app.generic.verifier.models import AcceptProofRequest, SendProofRequest
from app.util.did import ed25519_verkey_to_did_key
from shared.models.protocol import PresentProofProtocolVersion

logger = logging.getLogger(__name__)


class VerifierFacade(Enum):
    v1 = VerifierV1
    v2 = VerifierV2


def get_verifier_by_version(
    version_candidate: Union[str, PresentProofProtocolVersion]
) -> Verifier:
    if version_candidate == PresentProofProtocolVersion.v1 or (
        isinstance(version_candidate, str) and version_candidate.startswith("v1-")
    ):
        return VerifierFacade.v1.value
    elif (
        version_candidate == PresentProofProtocolVersion.v2
        or version_candidate.startswith("v2-")
    ):
        return VerifierFacade.v2.value
    else:
        raise ValueError(f"Unknown protocol version {version_candidate}")


async def assert_valid_prover(
    aries_controller: AcaPyClient, presentation: AcceptProofRequest, prover: Verifier
) -> None:
    """Check transaction requirements against trust registry for prover"""
    # get connection record
    proof_id = presentation.proof_id

    connection_id = await get_connection_from_proof(
        aries_controller=aries_controller, proof_id=proof_id, prover=prover
    )

    # TODO: (In other PR) handle case where no connection id exists
    # instead of simply rejecting the request
    if not connection_id:
        raise CloudApiException(
            "No connection id associated with proof request. Can not verify proof request",
            400,
        )

    connection_record = await get_connection_record(
        aries_controller=aries_controller,
        connection_id=connection_id,
    )

    if not connection_record.connection_id:
        raise CloudApiException("Cannot proceed. No connection id", 404)

    invitation_key = connection_record.invitation_key
    # Case 1: connection made with publid DID
    if connection_record.their_public_did:
        public_did = f"did:sov:{connection_record.their_public_did}"
    # Case 2: connection made with public DID
    elif connection_record.invitation_key:
        invitation_key = connection_record.invitation_key
        public_did = ed25519_verkey_to_did_key(key=invitation_key)
    else:
        raise CloudApiException("Could not determine did of the verifier", 400)

    # Try get actor from TR
    actor = await get_actor(did=public_did)

    # 2. Check actor has role verifier
    if not is_verifier(actor=actor):
        raise CloudApiException("Actor is missing required role 'verifier'", 403)

    # Get schema ids
    schema_ids = await get_schema_ids(
        aries_controller=aries_controller, presentation=presentation.presentation_spec
    )

    # Verify the schemas are actually in the list from TR
    if not await are_valid_schemas(schema_ids=schema_ids):
        raise CloudApiException(
            "Presentation is using schemas not registered in trust registry", 403
        )


async def assert_valid_verifier(
    aries_controller: AcaPyClient,
    proof_request: SendProofRequest,
):
    """Check transaction requirements against trust registry for verifier"""

    # 1. Check agent has public did
    # CASE: Agent has public DID
    try:
        public_did = await assert_public_did(aries_controller=aries_controller)
    except Exception:
        # CASE: Agent has NO public DID
        # check via connection -> invitation key
        connection_record = await get_connection_record(
            aries_controller=aries_controller,
            connection_id=proof_request.connection_id,
        )
        # get invitation key
        invitation_key = connection_record.invitation_key

        if not invitation_key:
            raise CloudApiException("Connection has no invitation key", 400)
        public_did = ed25519_verkey_to_did_key(invitation_key)

    # Try get actor from TR
    actor = await get_actor(did=public_did)

    # 2. Check actor has role verifier, raise exception otherwise
    if not is_verifier(actor=actor):
        raise CloudApiException(
            f"{actor['name']} is not a valid verifier in the trust registry.", 403
        )


async def are_valid_schemas(schema_ids: List[str]) -> bool:
    schemas_from_tr = await get_trust_registry_schemas()

    schemas_valid_list = [id in schemas_from_tr for id in schema_ids]

    return all(schemas_valid_list)


def is_verifier(actor: Actor) -> bool:
    return "verifier" in actor["roles"]


async def get_actor(did: str) -> Actor:
    actor = await actor_by_did(did)
    # Verify actor was in TR
    if not actor:
        raise CloudApiException(f"No actor with DID {did}.", 404)
    return actor


async def get_schema_ids(
    aries_controller: AcaPyClient, presentation: IndyPresSpec
) -> List[str]:
    """Get schema ids from credentials that will be revealed in the presentation"""
    revealed_schema_ids: Set[str] = set()

    revealed_attr_cred_ids = [
        attr.cred_id
        for _, attr in presentation.requested_attributes.items()
        if attr.revealed
    ]
    revealed_pred_cred_ids = [
        pred.cred_id for _, pred in presentation.requested_predicates.items()
    ]

    revealed_cred_ids = set([*revealed_attr_cred_ids, *revealed_pred_cred_ids])

    for revealed_cred_id in revealed_cred_ids:
        credential = await aries_controller.credentials.get_record(
            credential_id=revealed_cred_id
        )
        if credential.schema_id:
            revealed_schema_ids.add(credential.schema_id)

    return list(revealed_schema_ids)


async def get_connection_from_proof(
    aries_controller: AcaPyClient, prover: Verifier, proof_id: str
) -> Optional[str]:
    proof_record = await prover.get_proof_record(
        controller=aries_controller, proof_id=proof_id
    )
    return proof_record.connection_id


async def get_connection_record(
    aries_controller: AcaPyClient,
    connection_id: str,
) -> ConnRecord:
    """Retrieve the connection record"""
    return await aries_controller.connection.get_connection(conn_id=connection_id)
