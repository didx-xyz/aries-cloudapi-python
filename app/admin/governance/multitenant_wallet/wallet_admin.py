import json
from enum import Enum

from aiohttp import ClientError
from datetime import datetime

from typing import Optional, Dict, List

import logging
from aries_cloudcontroller import AcaPyClient
from pydantic import BaseModel

from dependencies import member_admin_agent, admin_agent_selector
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/wallet-multitenant", tags=["admin: wallet"])


class KeyManagementMode(Enum):
    managed = "managed"
    unmanaged = "unmanaged"


class WalletDispatchType(Enum):
    default = "default"
    both = "both"
    base = "base"


class WalletType(Enum):
    askar = "askar"
    in_memory = "in_memory"
    indy = "indy"


"""    "CreateWalletRequest": {
      "properties": {
        "image_url": {
          "description": "Image url for this wallet. This image url is publicized            (self-attested) to other agents as part of forming a connection.",
          "example": "https://aries.ca/images/sample.png",
          "type": "string"
        },
        "key_management_mode": {
          "description": "Key management method to use for this wallet.",
          "enum": [
            "managed"
          ],
          "example": "managed",
          "type": "string"
        },
        "label": {
          "description": "Label for this wallet. This label is publicized            (self-attested) to other agents as part of forming a connection.",
          "example": "Alice",
          "type": "string"
        },
        "wallet_dispatch_type": {
          "description": "Webhook target dispatch type for this wallet.             default - Dispatch only to webhooks associated with this wallet.             base - Dispatch only to webhooks associated with the base wallet.             both - Dispatch to both webhook targets.",
          "enum": [
            "default",
            "both",
            "base"
          ],
          "example": "default",
          "type": "string"
        },
        "wallet_key": {
          "description": "Master key used for key derivation.",
          "example": "MySecretKey123",
          "type": "string"
        },
        "wallet_name": {
          "description": "Wallet name",
          "example": "MyNewWallet",
          "type": "string"
        },
        "wallet_type": {
          "description": "Type of the wallet to create",
          "enum": [
            "askar",
            "in_memory",
            "indy"
          ],
          "example": "indy",
          "type": "string"
        },
        "wallet_webhook_urls": {
          "description": "List of Webhook URLs associated with this subwallet",
          "items": {
            "description": "Optional webhook URL to receive webhook messages",
            "example": "http://localhost:8022/webhooks",
            "type": "string"
          },
          "type": "array"
        }
      },
      "type": "object"
    },
"""


class CreateWalletRequest(BaseModel):
    image_url: Optional[str]
    label: str
    wallet_key: str
    wallet_name: str

    key_management_mode: KeyManagementMode = KeyManagementMode.managed
    wallet_dispatch_type: WalletDispatchType = WalletDispatchType.default
    wallet_type: WalletType = WalletType.indy
    wallet_webhook_urls: List[str] = []


"""    "CreateWalletResponse": {
      "properties": {
        "created_at": {
          "description": "Time of record creation",
          "example": "2021-07-12 07:31:03Z",
          "pattern": "^\\d{4}-\\d\\d-\\d\\d[T ]\\d\\d:\\d\\d(?:\\:(?:\\d\\d(?:\\.\\d{1,6})?))?(?:[+-]\\d\\d:?\\d\\d|Z|)$",
          "type": "string"
        },
        "key_management_mode": {
          "description": "Mode regarding management of wallet key",
          "enum": [
            "managed",
            "unmanaged"
          ],
          "type": "string"
        },
        "settings": {
          "description": "Settings for this wallet.",
          "type": "object"
        },
        "state": {
          "description": "Current record state",
          "example": "active",
          "type": "string"
        },
        "token": {
          "description": "Authorization token to authenticate wallet requests",
          "example": "eyJhbGciOiJFZERTQSJ9.eyJhIjogIjAifQ.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
          "type": "string"
        },
        "updated_at": {
          "description": "Time of last record update",
          "example": "2021-07-12 07:31:03Z",
          "pattern": "^\\d{4}-\\d\\d-\\d\\d[T ]\\d\\d:\\d\\d(?:\\:(?:\\d\\d(?:\\.\\d{1,6})?))?(?:[+-]\\d\\d:?\\d\\d|Z|)$",
          "type": "string"
        },
        "wallet_id": {
          "description": "Wallet record ID",
          "example": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "type": "string"
        }
      },
      "required": [
        "key_management_mode",
        "wallet_id"
      ],
      "type": "object"
    },
"""


class CreateWalletResponse(BaseModel):
    created_at: Optional[datetime]
    key_management_mode: KeyManagementMode
    settings: Optional[Dict]
    token: Optional[str]
    updated_at: Optional[datetime]
    wallet_id: str
    state: Optional[str]


"""
  "WalletRecord": {
      "properties": {
        "created_at": {
          "description": "Time of record creation",
          "example": "2021-07-12 07:31:03Z",
          "pattern": "^\\d{4}-\\d\\d-\\d\\d[T ]\\d\\d:\\d\\d(?:\\:(?:\\d\\d(?:\\.\\d{1,6})?))?(?:[+-]\\d\\d:?\\d\\d|Z|)$",
          "type": "string"
        },
        "key_management_mode": {
          "description": "Mode regarding management of wallet key",
          "enum": [
            "managed",
            "unmanaged"
          ],
          "type": "string"
        },
        "settings": {
          "description": "Settings for this wallet.",
          "type": "object"
        },
        "state": {
          "description": "Current record state",
          "example": "active",
          "type": "string"
        },
        "updated_at": {
          "description": "Time of last record update",
          "example": "2021-07-12 07:31:03Z",
          "pattern": "^\\d{4}-\\d\\d-\\d\\d[T ]\\d\\d:\\d\\d(?:\\:(?:\\d\\d(?:\\.\\d{1,6})?))?(?:[+-]\\d\\d:?\\d\\d|Z|)$",
          "type": "string"
        },
        "wallet_id": {
          "description": "Wallet record ID",
          "example": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "type": "string"
        }
      },
      "required": [
        "key_management_mode",
        "wallet_id"
      ],
      "type": "object"
    }"""


class WalletRecord(BaseModel):
    created_at: Optional[datetime]
    key_management_mode: KeyManagementMode
    settings: Optional[Dict]
    updated_at: Optional[datetime]
    wallet_id: str
    state: Optional[str]


class WalletList(BaseModel):
    results: List[WalletRecord]


"""    "CreateWalletTokenResponse": {
      "properties": {
        "token": {
          "description": "Authorization token to authenticate wallet requests",
          "example": "eyJhbGciOiJFZERTQSJ9.eyJhIjogIjAifQ.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
          "type": "string"
        }
      },
      "type": "object"
    },"""


class CreateWalletTokenResponse(BaseModel):
    token: str


"""
   "UpdateWalletRequest": {
      "properties": {
        "image_url": {
          "description": "Image url for this wallet. This image url is publicized            (self-attested) to other agents as part of forming a connection.",
          "example": "https://aries.ca/images/sample.png",
          "type": "string"
        },
        "label": {
          "description": "Label for this wallet. This label is publicized            (self-attested) to other agents as part of forming a connection.",
          "example": "Alice",
          "type": "string"
        },
        "wallet_dispatch_type": {
          "description": "Webhook target dispatch type for this wallet.             default - Dispatch only to webhooks associated with this wallet.             base - Dispatch only to webhooks associated with the base wallet.             both - Dispatch to both webhook targets.",
          "enum": [
            "default",
            "both",
            "base"
          ],
          "example": "default",
          "type": "string"
        },
        "wallet_webhook_urls": {
          "description": "List of Webhook URLs associated with this subwallet",
          "items": {
            "description": "Optional webhook URL to receive webhook messages",
            "example": "http://localhost:8022/webhooks",
            "type": "string"
          },
          "type": "array"
        }
      },
      "type": "object"
   }"""


class UpdateWalletRequest(BaseModel):
    image_url: Optional[str]
    label: Optional[str]
    wallet_dispatch_type: Optional[WalletDispatchType] = WalletDispatchType.default
    wallet_webhook_urls: Optional[List[str]]


# TODO: This should be somehow restricted?!
@router.post("/create-wallet", response_model=CreateWalletResponse)
async def create_subwallet(
    wallet_payload: CreateWalletRequest,
    aries_controller: AcaPyClient = Depends(admin_agent_selector),
) -> CreateWalletResponse:
    """
    Create a new wallet

    Parameters:
    -----------
    wallet_payload: CreateWalletRequest
        The payload for creating the wallet


    Returns:
    --------
    The response object from creating a wallet on the ledger

    Example Request Body:
    {
            "image_url": "https://aries.ca/images/sample.png",
            "key_management_mode": "managed",
            "label": "YOMA",
            "wallet_dispatch_type": "default",
            "wallet_key": "MySecretKey1234",
            "wallet_name": "YOMAsWallet",
            "wallet_type": "indy"
        }
    """
    # set wallet statics:
    if wallet_payload:
        wallet_response = await aries_controller.multitenancy.create_wallet(
            body=json.loads(wallet_payload.json())
        )
    return wallet_response


@router.delete("/{wallet_id}")
async def remove_subwallet_by_id(
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(admin_agent_selector),
):
    """
    Remove subwallet by id.

    Parameters:
    wallet_id: str
    """
    try:
        response = await aries_controller.multitenancy.remove_subwallet_by_id(wallet_id)
        if response == {}:
            return {"status": "Successfully removed wallet"}
        else:
            raise HTTPException(500, "Unable to delete sub wallet")
    except ClientError as client_error:
        if client_error.value.status == 401:
            return HTTPException(401, "subwallet to delete is not found")


@router.get("/{wallet_id}/auth-token", response_model=CreateWalletTokenResponse)
async def get_subwallet_auth_token(
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(admin_agent_selector),
):
    return await aries_controller.multitenancy.get_subwallet_authtoken_by_id(
        wallet_id=wallet_id
    )


@router.post("/{wallet_id}", response_model=WalletRecord)
async def update_subwallet(
    payload: UpdateWalletRequest,
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(member_admin_agent),
) -> WalletRecord:
    """
    Update subwallet by id.

    Parameters:
    -----------
    payload: UpdateWalletRequest
      payload for updating a subwallet
    wallet_id: str

    Returns:
    ---------
    The response object from updating a subwallet.
    """
    return await aries_controller.multitenancy.update_subwallet_by_id(
        json.loads(
            payload.json(exclude_unset=True, exclude_defaults=True, exclude_none=True)
        ),
        wallet_id,
    )


@router.get("/query-subwallet", response_model=WalletList)
async def query_subwallet(
    wallet_name: str = None,
    aries_controller: AcaPyClient = Depends(member_admin_agent),
) -> WalletList:

    """
    Query subwallets.

    Parameters:
    -----------
    wallet_name: str (Optional)

    """
    return await aries_controller.multitenancy.query_subwallets(wallet_name=wallet_name)


@router.get("/{wallet_id}", response_model=WalletRecord)
async def get_subwallet(
    wallet_id: str,
    aries_controller: AcaPyClient = Depends(member_admin_agent),
) -> WalletRecord:
    """
    Retrieve subwallet by id.

    Parameters:
    -------------
    wallet_id: str
    """
    return await aries_controller.multitenancy.get_single_subwallet_by_id(wallet_id)
