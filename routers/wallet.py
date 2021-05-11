from fastapi import APIRouter

import aries_cloudcontroller
### Import the AriesAgentController to do the work

router = APIRouter()


@router.get("/wallets", tags=["wallets"])
async def wallets_root():
    """
    The default endpoints for wallets

    TODO: Determine what this should return or
    whether this should return anything at all
    """
    return {"message": "Hello from the wallets controller"}


@router.post("/wallets", tags=["wallets"])
async def create_wallet():
    """
    Create a new wallet
    """
    pass


@router.get("/wallets/{wallet_id}", tags=["wallets"])
async def create_wallet(body: dict = {}):
    """
    Get the wallet information by id
    """
    pass


@router.get("/wallets/{wallet_id}/connections", tags=["wallets", "connections"])
async def get_connections():
    """
    Get all connections for a wallet given the wallet's ID
    """
    pass


@router.get(
    "/wallets/{wallet_id}/connections/{conn_id}", tags=["wallets", "connections"]
)
async def get_connection_by_id(operation: str, body: dict = {}):
    """
    Get the specific connections per wallet per connection
    by respective IDs
    """
    pass


@router.post("/wallets/{wallet_id}/connections", tags=["wallets", "connections"])
async def create_connection_by_id(operation: str, body: dict = {}):
    """
    Create a connection for a wallet
    """
    pass


@router.put(
    "/wallets/{wallet_id}/connections/{conn_id}", tags=["wallets", "connections"]
)
async def update_connection_by_id(operation: str, body: dict = {}):
    """
    Update a specific connection (by ID) for a
    given wallet (by ID)
    """
    pass


@router.delete(
    "/wallets/{wallet_id}/connections/{conn_id}", tags=["wallets", "connections"]
)
async def delete_connection_by_id(operation: str, body: dict = {}):
    """
    Delete a connection (by ID) for a given wallet (by ID)
    """
    pass


@router.delete("/wallets/{wallet_id}", tags=["wallets", "connections"])
async def delete_connection_by_id(operation: str, body: dict = {}):
    """
    Delete a wallet (by ID)

    TODO: SHould this be admin-only?
    """
    pass
