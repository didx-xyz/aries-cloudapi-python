from typing import Optional
import logging

from app.util.did import ed25519_verkey_to_did_key

from aries_cloudcontroller import AcaPyClient, ConnRecord
from app.facades.trust_registry import (
    Actor,
    actor_by_did,
    get_trust_registry_schemas,
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
        pub_did = ed25519_verkey_to_did_key(invitation_key)
    # Try get actor from TR
    actor = await get_actor(did=pub_did)
    # 2. Check actor has role verifier, raise exception otherwise
    if not is_verifier(actor=actor):
        raise CloudApiException(
            f"{actor['name']} is not a valid verifier in the trust registry."
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
    if connection_record.their_public_did:
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
    schema_ids = await get_schema_ids(aries_controller=aries_controller)

    # Verify the schemas are actually in the list from TR
    if await is_valid_schemas(schema_ids=schema_ids):
        return True
    else:
        raise CloudApiException("Could not verify prover against trust registry", 401)


async def is_valid_schemas(schema_ids: list) -> Optional[bool]:
    schemas_from_tr = await get_trust_registry_schemas()
    schemas_valid_list = [id in schemas_from_tr for id in schema_ids]
    if not all(schemas_valid_list):
        # Could additionally return the schema ID(s) that aren't found.
        # Not sure that's any useful, though
        raise CloudApiException(
            f"Found schema unknown to trust registrty\n{schemas_from_tr} \n {schemas_valid_list}",
            400,
        )
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


async def get_schema_ids(aries_controller: AcaPyClient) -> list:
    cred_records = await aries_controller.credentials.get_records()
    schema_ids = [rec.schema_id for rec in cred_records.results]
    return schema_ids


async def get_connection_from_proof(
    aries_controller: AcaPyClient, prover: Verifier, proof_id: str
) -> str:
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
