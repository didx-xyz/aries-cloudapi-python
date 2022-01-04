import base58
from typing import List, Literal, Optional
import logging

from aries_cloudcontroller import AcaPyClient, ConnRecord
from .models import ProofRequestBase
from app.facades.trust_registry import (
    Actor,
    actor_by_did,
    actor_has_role,
    get_trust_registry,
)
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.error.cloud_api_error import CloudApiException
from app.facades.acapy_wallet import assert_public_did, has_public_did

logger = logging.getLogger(__name__)


# VERIFIER
async def check_tr_for_verifier(
    aries_controller: AcaPyClient, prover: Verifier, proof_request
) -> Optional[bool]:
    """Check transaction requirements against trust registry for verifier"""
    # 1. Check agent has public did
    agent_has_public_did = await has_public_did(aries_controller=aries_controller)
    # CASE: Agent has public DID
    if agent_has_public_did:
        # Verify actor is registered in trust registry
        pub_did = await assert_public_did(aries_controller=aries_controller)
    # CASE: Agent has NO public DID
    else:
        ## check via connection -> invitation key
        # get connection record
        connection_record = await get_connection_record(
            aries_controller=aries_controller,
            prover=prover,
            proof_id=proof_request.proof_id,
        )
        # get invitation key
        invitation_key = connection_record.invitation_key
        pub_did = f"did:sov:{invitation_key}"

    # Try get actor from TR
    actor = await get_actor(did=pub_did)

    # 2. Check actor has role verifier
    await check_is_verifier(actor_id=actor.id)

    # 3. Verify schema ID(s) are registered in trust registry
    # unique credential_ids of revealed attrs
    credential_ids = get_credential_ids(proof_request=proof_request)

    schema_ids = await get_schema_ids(
        aries_controller=aries_controller, credential_ids=credential_ids
    )

    # # Verify the schemas are actually in the list from TR
    if check_schemas_valid(aries_controller=aries_controller, schema_ids=schema_ids):
        return True


# PROVER
async def check_tr_for_prover(
    aries_controller: AcaPyClient, prover: Verifier, proof_request
) -> Optional[bool]:
    """Check transaction requirements against trust registry for prover"""
    # get connection record
    connection_record = await get_connection_record(
        aries_controller=aries_controller,
        prover=prover,
        proof_id=proof_request.proof_id,
    )

    # TODO: (In other PR) handle case where no conneciton id exists
    # instead of simply rejecting the request
    if not connection_record.connection_id:
        raise CloudApiException(f"Cannot proceed. No connection ID", 404)

    # Case 1: connection NOT made with publid DID
    if (
        not connection_record.their_public_did
        or connection_record.their_public_did == ""
    ):
        pub_did = f"did:sov:{connection_record.their_public_did}"
    # Case 2: connection made with public DID
    else:
        invitation_key = connection_record.invitation_key
        pub_did = ed25519_verkey_to_did_key(key=invitation_key)

    # Try get actor from TR
    actor = await get_actor(did=pub_did)

    # 2. Check actor has role verifier
    await check_is_verifier(actor_id=actor.id)

    # unique credential_ids of revealed attrs
    credential_ids = get_credential_ids(proof_request=proof_request)

    schema_ids = await get_schema_ids(
        aries_controller=aries_controller, credential_ids=credential_ids
    )

    # # Verify the schemas are actually in the list from TR
    if check_schemas_valid(aries_controller=aries_controller, schema_ids=schema_ids):
        return True


async def check_schemas_valid(aries_controller: AcaPyClient, schema_ids: list) -> bool:
    schemas_from_tr = (await get_trust_registry())["schemas"]
    # Verify the schemas are actually in the list from TR
    schemas_valid_list = [id in schemas_from_tr for id in schema_ids]
    if not all(schemas_valid_list):
        # Could additionally return the schema ID(s) that aren't found.
        # Not sure that's any useful, though
        raise CloudApiException("schema(s) unknown to trust registrty", 400)


async def get_schema_ids(aries_controller: AcaPyClient, credential_ids: list) -> list:
    schema_ids = [
        (await aries_controller.credentials.get_record(credential_id=id)).schema_id
        for id in credential_ids
    ]
    return schema_ids


async def check_is_verifier(actor_id: str) -> bool:
    is_verifier = await actor_has_role(actor_id=actor_id, role="verifier")
    if not is_verifier:
        raise CloudApiException("Insufficient priviliges: Actor not a verifier", 401)
    return is_verifier


async def get_actor(did: str) -> Optional[Actor]:
    actor = await actor_by_did(did)
    # Verify actor was in TR
    if not actor:
        raise CloudApiException(f"No actor with DID {did}", 404)
    return actor


def attrs_generator(
    proof_request: ProofRequestBase,
    search_term: Literal[
        "requested_attributes",
        "requested_predicates",
    ],
) -> List:
    """Finds given key and return its value from any depths of a proof request object

    This is required because the proof_request can be different model stuctures.
    See also: app/generic/verifier/models.py

    The requested_attributes and requested_predicates to under different paths for different models.
    """
    proof_request_dict = proof_request.dict()
    for k, v in proof_request_dict.items():
        if k == search_term:
            yield v
        elif isinstance(v, dict):
            for val in attrs_generator(v, search_term):
                yield val


def get_credential_ids(proof_request: ProofRequestBase) -> List:
    """Get a list of unique credential ids"""
    credential_ids = []
    for term in ["requested_attributes", "requested_predicates"]:
        requested_terms = [
            x for x in attrs_generator(proof_request=proof_request, search_term=term)
        ]
        req_terms = [requested for term in requested_terms for requested in term]
        credential_ids.append(req_terms)
    return list(set(credential_ids))


async def get_connection_record(
    aries_controller: AcaPyClient, prover: Verifier, proof_id: str
) -> ConnRecord:
    """Retrieve the connection record"""
    # get connection ID
    connection_id = (
        await prover.get_proof_record(controller=aries_controller, proof_id=proof_id)
    ).connection_id
    # Get connection record
    return await aries_controller.connection.get_connection(conn_id=connection_id)


def ed25519_verkey_to_did_key(key: str) -> str:
    """Convert a naked ed25519 verkey to W3C did:key format."""

    key_bytes = base58.b58decode(key)
    prefixed_key_bytes = b"".join([b"\xed\x01", key_bytes])
    fingerprint = base58.b58encode(prefixed_key_bytes).decode("ascii")
    did_key = f"did:key:z{fingerprint}"
    return did_key
