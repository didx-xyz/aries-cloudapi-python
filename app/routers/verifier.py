import logging
import traceback
from typing import List, Optional

from fastapi import APIRouter, Header

from facade import (
    create_controller,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verifier")

# TODO verify that active connection exists
# Better tag?
@router.get("/request-proof-for-schema", tags=["proof", "verifier"])
async def get_proof_request(
    req_header: Header,
    connection_id: str,
    schema_id: str,
    requested_attrs: dict,
    revocation: int = None,
):
    """
    Hey I'm a doc string
    """

    # get attributes for schema using schema id

    # check attributes from get are set or superset of requested attrs

    ## if schame attrs and requested attrs mismatch return error

    # if revocation not None: Add revocation

    # TODO What exactly do we do with self-attested?

    # Set predicates for zero-knowledge proof

    # Construct indy_proof_request

    ## if revocation: add that to indy_proof-request

    # Create web version of the request:
    # proof_request_web_request = {
    #     "connection_id": connection_id,
    #     "proof_request": indy_proof_request,
    #     "trace": exchange_tracing,
    # }

    # Send the proof request

    # get the presentaiton exchange id

    #  verify using the presentaiton exchange id

    # check state is 'verified'
    ## if no, error? retry?
    ## if yes, continue

    # Extract revealed attributes

    # return revealed attributes

    try:
        async with create_controller(req_header) as controller:
            pass
    except Exception as e:
        raise e
