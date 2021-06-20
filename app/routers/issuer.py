import io
import logging
import os
import traceback
from typing import List, Optional

import qrcode
from facade import (
    create_controller,
    get_connection_id,
    get_cred_def_id,
    get_schema_attributes,
    issue_credentials,
    write_credential_def,
)
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/issuer")


admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
admin_api_key = os.getenv("ACAPY_ADMIN_API_KEY")
is_multitenant = os.getenv("IS_MULTITENANT", False)
ledger_url = os.getenv("LEDGER_NETWORK_URL")


@router.get("/issue-credential", tags=["issue", "credential"])
async def issue_credential(
    schema_id: str,
    connection_id: str,
    credential_attrs: List[str] = Query(None),
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
):
    """
    Issues a credential

    Parameters:
    -----------
    schema_id: str
    connection_id: str
    credential_attrs: List[str]
        A list of requested credential attributes
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        async with create_controller(auth_headers) as controller:

            # Check if connection is active
            # connection = await controller.get_connection(connection_id)
            # TODO we should somehow enble the check below. Yet we want to provide some time window/a chance
            # to establish an active connection eg via sending a basic message or trust ping
            # in case the connection is not auto-accepting/setting itself to active
            # if connection["state"] is not "active":
            #     raise HTTPException(status_code=403, detail="Connection not active")

            # TODO How do we want to handle this for input? This now assumes that the client knows
            # the schema attributes or is able to obtain them if it does not.
            schema_attr = await get_schema_attributes(controller, schema_id)
            # TODO The below call works but smells fishy. What should we really be doing here?
            # Should/Can't we just obtain the credential definition id from somewhere?
            # This should be written to the ledger already. Shouldn't this fail on trying
            # to write this again? However, this just returns the wanted cred_def_id.
            credential_def = await write_credential_def(controller, schema_id)

            # TODO Do we want to obtain cred_def_id from somewhere else
            cred_def_id = await get_cred_def_id(controller, credential_def)
            # TODO Should this validate the provided schame attrs from the client against the from the schema?
            # As in should we validate at this point that the sets of attributes match
            credential_attributes = [
                {"name": k, "value": v}
                for k, v in list(zip(schema_attr, credential_attrs))
            ]
            record = await issue_credentials(
                controller, connection_id, schema_id, cred_def_id, credential_attributes
            )

            # TODO Do we want to return the record or just success?
            return record
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to issue credential.The following error occured:\n{e!r}\n{err_trace}"
        )
        raise e


@router.get(
    "/connection",
    tags=["connection", "wallets"],
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Return the JSON item or an image.",
        }
    },
)
async def create_connection(
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
):
    """
    Creates invitation for the holder to scan

    Parameters:
    ----------
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns: StreamingResponse
        QRCode PNG file from StreamingResponse
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        async with create_controller(auth_headers) as controller:
            # TODO: Should this come from env var or from the client request?
            invite = await controller.connections.create_invitation()
            # connection_id = invite["connection_id"]
            inviteURL = invite["invitation_url"]

            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(inviteURL)
            qr.make(fit=True)
            img = qr.make_image(fill="black", back_color="white")
            buffer_img = io.BytesIO()
            img.save(buffer_img, format="PNG")
            resp_img = io.BytesIO(buffer_img.getvalue())
            return StreamingResponse(resp_img, media_type="image/png")
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to create qrcode. The following error occured:\n{e!r}\n{err_trace}"
        )
        raise e


# TODO Decide where this endpoint to lie
@router.get("/get-connection-id", tags=["connection"])
async def get_connection_ids(
    api_key: Optional[str] = Header(None),
    wallet_id: Optional[str] = Header(None),
    tenant_jwt: Optional[str] = Header(None),
):
    """
    Creates invitation for the holder to scan

    Parameters:
    ----------
    api_key: Header(None)
        The request header object api_key
    wallet_id: Header(None)
        The request header object wallet_id
    tenant_jwt: Header(None)
        The request header object tenant_jwt

    Returns:
    --------
    connection_id: JSON
        The request response from the ledger with all current connections
        The 'results' key holds a [dict].
    """
    auth_headers = {
        "api_key": api_key,
        "wallet_id": wallet_id,
        "tenant_jwt": tenant_jwt,
    }
    try:
        async with create_controller(auth_headers) as controller:
            # TODO: Should this come from env var or from the client request?
            connection = await get_connection_id(controller)
            return connection
    except Exception as e:
        err_trace = traceback.print_exc()
        logger.error(
            f"Failed to get connection ids.The following error occured:\n{e!r}\n{err_trace}"
        )
        raise e
