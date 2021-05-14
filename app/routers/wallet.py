from fastapi import APIRouter, HTTPException
import requests
import json

import aries_cloudcontroller

router = APIRouter()

# TODO: Determine how we want to instantiate and access the ariescontroller really.
# This is the very crude way MVP

aries_agent_controller = aries_cloudcontroller.AriesAgentController(
    # TODO get these params from config or some other more graceful way
    admin_url=f"http://multitenant-agent:3021",
    api_key="adminApiKey",
    is_multitenant=True,
)


@router.get("/wallets/create-pub-did", tags=["wallet", "did"])
async def create_public_did():
    """
    Create a new public DID and
    write it to the ledger and
    receive its public info.
    
    Returns:
    * DID
    * Issuer verkey
    * Issuer Endpoint
    """
    # TODO: make this url more dynamic for when this is not always sovrin
    url = "https://selfserve.sovrin.org/nym"
    # Adding empty header as parameters are being sent in payload
    generate_did_res = await aries_agent_controller.wallet.create_did()
    if not generate_did_res["result"]:
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not generate DID.\n{generate_did_res}",
        )
    did_object = generate_did_res["result"]
    payload = {
        "network": "stagingnet",
        "did": did_object["did"],
        "verkey": did_object["verkey"],
        "paymentaddr": "",
    }
    r = requests.post(url, data=json.dumps(payload), headers={})
    if r.status_code != 200:
        error_json = r.json()
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not write to StagingNet.\n{error_json}",
        )
    taa_response = await aries_agent_controller.ledger.get_taa()
    print("taa_response:\n", taa_response)
    if not taa_response["result"]:
        error_json = taa_response.json()
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not get TAA.\n{error_json}",
        )
    TAA = taa_response["result"]["taa_record"]
    TAA["mechanism"] = "service_agreement"
    accept_taa_response = await aries_agent_controller.ledger.accept_taa(TAA)
    print("accept_taa_response:\n", accept_taa_response)
    if accept_taa_response != {}:
        error_json = accept_taa_response.json()
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not accept TAA.\n{error_json}",
        )
    assign_pub_did_response = await aries_agent_controller.wallet.assign_public_did(
        did_object["did"]
    )
    print("assign_pub_did_response:\n", assign_pub_did_response)
    if not assign_pub_did_response["result"] or assign_pub_did_response["result"] == {}:
        error_json = assign_pub_did_response.json()
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not assign DID.\n{error_json}",
        )
    get_pub_did_response = await aries_agent_controller.wallet.get_public_did()
    print("get_pub_did_response:\n ", get_pub_did_response)
    if not get_pub_did_response["result"] or get_pub_did_response["result"] == {}:
        error_json = get_pub_did_response.json()
        raise HTTPException(
            status_code=418,
            detail=f"Something went wrong.\nCould not obtain public DID.\n{error_json}",
        )
    issuer_nym = get_pub_did_response["result"]["did"]
    issuer_verkey = get_pub_did_response["result"]["verkey"]
    issuer_endpoint = await aries_agent_controller.ledger.get_did_endpoint(issuer_nym)
    if not issuer_endpoint:
        raise HTTPException(
            status_code=418,
            detail="Something went wrong.\nCould not obtain issuer endpoint.",
        )
    final_response = {
        "did_object": did_object,
        "issuer_verkey": issuer_verkey,
        "issuer_endpoint": issuer_endpoint,
    }
    return final_response


@router.get("/wallets", tags=["wallets"])
async def wallets_root():
    """
    The default endpoints for wallets

    TODO: Determine what this should return or
    whether this should return anything at all
    """
    return {"message": "Hello from the wallets controller"}


@router.post("/wallets", tags=["wallets"])
async def create_wallet(wallet_payload: dict = None):
    """
    Create a new wallet
    """
    try:
        if aries_agent_controller.is_multitenant:
            # TODO replace with model for payload/wallet like
            # described https://fastapi.tiangolo.com/tutorial/body/
            if not wallet_payload:
                payload = {
                    "image_url": "https://aries.ca/images/sample.png",
                    "key_management_mode": "managed",
                    "label": "Alice",
                    "wallet_dispatch_type": "default",
                    "wallet_key": "MySecretKey1234",
                    "wallet_name": "AlicesWallet",
                    "wallet_type": "indy",
                }
            else:
                payload = wallet_payload
            wallet_response = await aries_agent_controller.multitenant.create_wallet(
                payload
            )
        else:
            wallet_response = await aries_agent_controller.wallets.create_did()
        return wallet_response
    except Exception as e:
        raise e(f"Could not complete request because the following error occured: {e}")


@router.get("/wallets/{wallet_id}", tags=["wallets"])
async def create_wallet(wallet_id):
    """
    Get the wallet information by id
    """
    pass


@router.get("/wallets/{wallet_id}/connections", tags=["wallets", "connections"])
async def get_connections(wallet_id):
    """
    Get all connections for a wallet given the wallet's ID
    """
    pass


@router.get(
    "/wallets/{wallet_id}/connections/{conn_id}", tags=["wallets", "connections"]
)
async def get_connection_by_id(wallet_id, connection_id):
    """
    Get the specific connections per wallet per connection
    by respective IDs
    """
    pass


@router.post("/wallets/{wallet_id}/connections", tags=["wallets", "connections"])
async def create_connection_by_id(wallet_id):
    """
    Create a connection for a wallet
    """
    pass


@router.put(
    "/wallets/{wallet_id}/connections/{conn_id}", tags=["wallets", "connections"]
)
async def update_connection_by_id(wallet_id, connection_id):
    """
    Update a specific connection (by ID) for a
    given wallet (by ID)
    """
    pass


@router.delete(
    "/wallets/{wallet_id}/connections/{conn_id}", tags=["wallets", "connections"]
)
async def delete_connection_by_id(wallet_id, connection_id):
    """
    Delete a connection (by ID) for a given wallet (by ID)
    """
    pass


@router.delete("/wallets/{wallet_id}", tags=["wallets", "connections"])
async def delete_connection_by_id(wallet_id):
    """
    Delete a wallet (by ID)

    TODO: Should this be admin-only?
    """
    pass
