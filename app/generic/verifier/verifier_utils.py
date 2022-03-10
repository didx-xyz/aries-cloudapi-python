import base58
import json
from typing import List, Literal, Optional
import logging

from aries_cloudcontroller import AcaPyClient, ConnRecord
from .models import ProofRequestBase
from app.facades.trust_registry import (
    Actor,
    actor_by_did,
    get_trust_registry,
)
from app.generic.verifier.facades.acapy_verifier import Verifier
from app.error.cloud_api_error import CloudApiException
from app.facades.acapy_wallet import assert_public_did

logger = logging.getLogger(__name__)


# VERIFIER
async def check_tr_for_verifier(
    aries_controller: AcaPyClient,
    proof_request,
) -> Optional[bool]:
    """Check transaction requirements against trust registry for verifier"""
    # 1. Check agent has public did
    # CASE: Agent has public DID
    try:
        pub_did = await assert_public_did(aries_controller=aries_controller)
    except Exception:
        # CASE: Agent has NO public DID
        ## check via connection -> invitation key
        connection_record = await get_connection_record(
            aries_controller=aries_controller,
            connection_id=proof_request.connection_id,
        )
        # get invitation key
        invitation_key = connection_record.invitation_key
        pub_did = f"did:sov:{invitation_key}"
    # Try get actor from TR
    actor = await get_actor(did=pub_did)
    # 2. Check actor has role verifier, raise exception otherwise
    if not is_verifier(actor=actor):
        raise CloudApiException(
            f"{actor} is not a valid verifier in the trust registry."
        )
    else:
        return True


# PROVER
async def check_tr_for_prover(
    aries_controller: AcaPyClient, prover: Verifier, proof_request
) -> Optional[bool]:
    """Check transaction requirements against trust registry for prover"""
    # get connection record
    proof_id = proof_request.proof_id
    connection_id = await get_connection_from_proof(
        aries_controller=aries_controller, proof_id=proof_id, prover=prover
    )
    connection_record = await get_connection_record(
        aries_controller=aries_controller,
        connection_id=connection_id,
    )
    # TODO: (In other PR) handle case where no conneciton id exists
    # instead of simply rejecting the request
    if not connection_record.connection_id:
        raise CloudApiException(f"Cannot proceed. No connection ID", 404)

    # Case 1: connection NOT made with publid DID
    if connection_record.their_public_did and connection_record.their_public_did != "":
        pub_did = f"did:sov:{connection_record.their_public_did}"
    # Case 2: connection made with public DID
    else:
        invitation_key = connection_record.invitation_key
        pub_did = ed25519_verkey_to_did_key(key=invitation_key)

    # Try get actor from TR
    actor = await get_actor(did=pub_did)
    # 2. Check actor has role verifier
    if not is_verifier(actor=actor):
        raise CloudApiException("Could not verify prover against trust registry", 401)

    # Get schema ids
    schema_ids = await get_schema_ids(aries_controller=aries_controller, prover=prover)

    # Verify the schemas are actually in the list from TR
    if await is_valid_schemas(schema_ids=schema_ids):
        return True
    else:
        raise CloudApiException("Could not verify prover against trust registry", 401)


async def is_valid_schemas(schema_ids: list) -> Optional[bool]:
    schemas_from_tr = (await get_trust_registry())["schemas"]
    schemas_valid_list = [id in schemas_from_tr for id in schema_ids]
    if not all(schemas_valid_list):
        # Could additionally return the schema ID(s) that aren't found.
        # Not sure that's any useful, though
        raise CloudApiException("Found schema unknown to trust registrty", 400)
    return True


def is_verifier(actor: Actor) -> bool:
    if not "verifier" in actor["roles"]:
        raise CloudApiException("Insufficient priviliges: Actor not a verifier.", 401)
    return True


async def get_actor(did: str) -> Optional[Actor]:
    actor = await actor_by_did(did)
    # Verify actor was in TR
    if not actor:
        raise CloudApiException(f"No actor with DID {did}.", 404)
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
    # If the proof_request in not a dict already make it one
    if not isinstance(proof_request, dict):
        proof_request = proof_request.dict()
    for k, v in proof_request.items():
        if k == search_term:
            yield v
        elif isinstance(v, dict):
            for val in attrs_generator(v, search_term):
                yield val


async def get_schema_ids(aries_controller: AcaPyClient) -> list:
    cred_records = json.loads((await aries_controller.credentials.get_records()).json())
    schema_ids = [rec["schema_id"] for rec in cred_records["results"]]
    return schema_ids


def get_credential_ids(proof_request: ProofRequestBase) -> List:
    """Get a list of unique credential ids"""
    credential_ids = []
    for term in ["requested_attributes", "requested_predicates"]:
        requested_terms = [
            x for x in attrs_generator(proof_request=proof_request, search_term=term)
        ]
        if None in requested_terms:
            credential_ids.extend([None])
        else:
            req_terms = [
                requested
                for term in requested_terms
                for requested in term
                if term != None
            ]
            credential_ids.extend(req_terms)
    return list(set(credential_ids))


async def get_connection_from_proof(
    aries_controller: AcaPyClient, prover: Verifier, proof_id: str
) -> str:
    proof_records = await prover.get_proof_records(aries_controller)
    associated_proofs = [p for p in proof_records if p.proof_id == proof_id]
    return associated_proofs[0].connection_id


async def get_connection_record(
    aries_controller: AcaPyClient,
    connection_id: str,
) -> ConnRecord:
    """Retrieve the connection record"""
    return await aries_controller.connection.get_connection(conn_id=connection_id)


def ed25519_verkey_to_did_key(key: str) -> str:
    """Convert a naked ed25519 verkey to W3C did:key format."""

    key_bytes = base58.b58decode(key)
    prefixed_key_bytes = b"".join([b"\xed\x01", key_bytes])
    fingerprint = base58.b58encode(prefixed_key_bytes).decode("ascii")
    did_key = f"did:key:{fingerprint}"
    return did_key
