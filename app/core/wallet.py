import logging

from distutils.util import strtobool
import os

import acapy_ledger_facade
from facade import create_controller
import acapy_wallet_facade as wallet_facade
from schemas import DidCreationResponse
import ledger_facade

logger = logging.getLogger(__name__)

is_multitenant = strtobool(os.getenv("IS_MULTITENANT", "False"))


async def create_public_did(req_header: str) -> DidCreationResponse:
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.

    Returns:
    * DID object (json)
    * Issuer verkey (str)
    * Issuer Endpoint (url)
    """
    # TODO Can we break down this endpoint into smaller functions?
    # Because this really is too complex/too much happening at once.
    # This way not really testible/robust
    async with create_controller(req_header) as aries_agent_controller:
        # TODO: Should this come from env var or from the client request?
        # Adding empty header as parameters are being sent in payload
        generate_did_res = await wallet_facade.create_did(aries_agent_controller)
        did_object = generate_did_res["result"]
        await ledger_facade.get_nym(did_object)

        taa_response = await acapy_ledger_facade.get_taa(aries_agent_controller)

        await acapy_ledger_facade.accept_taa(aries_agent_controller, taa_response)
        await wallet_facade.assign_public_did(aries_agent_controller, did_object['did'])
        get_pub_did_response = await wallet_facade.get_public_did(aries_agent_controller)
        issuer_nym = get_pub_did_response["result"]["did"]
        issuer_verkey = get_pub_did_response["result"]["verkey"]
        issuer_endpoint = await acapy_ledger_facade.get_did_endpoint(aries_agent_controller,
                                                                     issuer_nym
                                                                     )
        issuer_endpoint_url = issuer_endpoint["endpoint"]
        final_response = DidCreationResponse(
            did_object=get_pub_did_response['result'],
            issuer_verkey=issuer_verkey,
            issuer_endpoint=issuer_endpoint_url,
        )
        return final_response
