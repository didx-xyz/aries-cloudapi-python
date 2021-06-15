import logging
import traceback
import time
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from facade import (
    create_controller,
    get_schema_attributes,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verifier")


# TODO verify that active connection exists
# Better tag?
@router.post("/request-proof-for-schema", tags=["proof", "verifier"])
async def get_proof_request(
    connection_id: str,
    schema_id: str,
    requested_attrs: List[str] = Query(None),  # Should be a list
    self_attested: str = None,  # What should this be? is this user input or does is come with the schema?
    zero_knowledge_proof: dict = None,
    revocation: int = None,
    exchange_tracing: bool = False,
    req_header: Optional[str] = Header(None),
):
    """
    Request proof of a (sub) set of attributes against a schema by ID.
    This may contain zero-knowledge attributes.
    This may contain revocation of the proof.
    """
    try:
        # get attributes for schema using schema id
        async with create_controller(req_header) as controller:
            schema_resp = await get_schema_attributes(controller, schema_id)
            if type(schema_resp) is not list:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to get schema. Got the following: {schema_resp!r}",
                )
            # Check if the required
            # check attributes from get are set or superset of requested attrs
            # TODO Obviously make this non-hardcoded
            # requested_attrs = ["age"]  # Let's just make this true for now
            is_attrs_match = all(x in schema_resp for x in requested_attrs)
            ## if schame attrs and requested attrs mismatch return error
            if not is_attrs_match:
                raise HTTPException(
                    status_code=400,
                    detail="Requested attributes not a (sub) set of schema attributes.",
                )
            # TODO Figure out what this is for behind the scenes
            attr_req = [
                {"name": k, "restrictions": [{"schema_id": schema_id}]}
                for k in requested_attrs
            ]
            logger.error(f"{is_attrs_match}")
            # if revocation not None: Add revocation
            if self_attested:
                [
                    attr_req.append({"name": att}) for att in self_attested
                ]  # append the self attested attrs
            # TODO What actually provided here? The attrubutes of revocation? The duration? And where do they come from?
            #
            revocation_attributes = []
            if revocation and len(revocation_attributes) > 0:
                [
                    attr_req.append(
                        {
                            "name": rev_attr,
                            "restrictions": [{"schema_id": schema_id}],
                            "non_revoked": {"to": int(time.time() - 1)},
                        }
                    )
                    for rev_attr in revocation_attributes
                ]
            # TODO What exactly do we do with self-attested?
            if self_attested:
                [attr_req.append({"name": att}) for att in self_attested]
            # Set predicates for zero-knowledge proof
            # The come in this form:  # Do they come from client input?
            # req_preds = [
            #     {
            #         "name": "age",
            #         "p_type": ">=",
            #         "p_value": 21,
            #         "restrictions": [{"schema_id": 1234}],
            #     },
            # ]
            req_preds = []
            if zero_knowledge_proof:
                [
                    req_preds.append(
                        {
                            "name": k["name"],
                            "p_type": k["p_type"],
                            "p_value": k["p_value"],
                            "restrictions": [{"schema_id": schema_id}],
                        }
                    )
                    for k in zero_knowledge_proof
                ]

            # Construct indy_proof_request
            indy_proof_request = {
                "name": "Proof of Completion of PyDentity SSI Tutorial",
                "version": schema_id.split(":")[-1],
                "requested_attributes": {
                    f"0_{req_attr['name']}_uuid": req_attr for req_attr in attr_req
                },
                "requested_predicates": {
                    f"0_{req_pred['name']}_GE_uuid": req_pred for req_pred in req_preds
                },
            }
            ## if revocation: add that to indy_proof-request
            if revocation:
                indy_proof_request["non_revoked"] = {"to": int(time.time())}

            # TODO Add exchange tracing True/False
            exchange_tracing = False
            # Create web version of the request:
            proof_request_web_request = {
                "connection_id": connection_id,
                "proof_request": indy_proof_request,
                "trace": exchange_tracing,
            }

            # Send the proof request
            response = await controller.proofs.send_request(proof_request_web_request)
            # get the presentaiton exchange id
            presentation_exchange_id = response["presentation_exchange_id"]

            return presentation_exchange_id
    except Exception as e:
        logger.error(f"Failed to request proof: \n {e}")
        raise e


@router.get("/verify-proof-request", tags=["verifier", "proof"])
async def verify_proof_request(
    presentation_exchange_id: str, req_header: Optional[str] = Header(None)
):

    try:
        async with create_controller(req_header) as controller:
            #  verify using the presentaiton exchange id
            verify = await controller.proofs.verify_presentation(
                presentation_exchange_id
            )

            # check state is 'verified'
            ## if no, error? retry?
            ## if yes, continue
            # Should we really raise here or rather inform or wait?
            if not verify["state"] == "verified":
                raise HTTPException(
                    status_code=400,
                    detail="Presentation state not verified!",
                )
                # return revealed attributes
            return verify
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to verify proof request. THe following error occured:\n{e!r}\n{err_trace}"
        )
        raise e
