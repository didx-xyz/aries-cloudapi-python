from fastapi import APIRouter

import aries_cloudcontroller

router = APIRouter()

# TODO: Determine how we want to instantiate and access the ariescontroller really.
# This is the very crude way MVP
http_port = "1234"

aries_agent_controller = aries_cloudcontroller.AriesAgentController(
    # TODO get these params from config or some other more graceful way
    admin_url = f"http://localhost:{http_port}",
    api_key = None,
    is_multitenant = True,
)

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
            wallet_response = await aries_agent_controller.multitenant.create_wallet(payload)
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
