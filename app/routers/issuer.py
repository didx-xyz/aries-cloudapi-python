from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List
import io
import qrcode
import aries_cloudcontroller
import os
from utils import (
    get_schema_attributes,
    write_credential_def,
    get_cred_def_id,
    issue_credential,
)

router = APIRouter(prefix="/issuer")


admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
admin_api_key = os.getenv("ACAPY_ADMIN_API_KEY")
is_multitenant = os.getenv("IS_MULTITENANT", False)
ledger_url = os.getenv("LEDGER_NETWORK_URL")


@router.get("/issue-credential", tags=["issue", "credential"])
async def issue_credential(
    schema_id: str, connection_id: str, credential_attrs: List[str] = Query(None)
):
    """
    Issues a credential
    """
    try:
        aries_agent_controller = aries_cloudcontroller.AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=admin_api_key,
            is_multitenant=is_multitenant,
        )

        # TODO check whether connection is in active state.
        # If not, return msg saying conneciton not active - should be active
        connection = await aries_agent_controller.get_connction(connection_id)
        if connection["state"] is not "active":
            raise HTTPException(
                status_code=404,
                detail="Connection not active",
            )

        schema_attr = await get_schema_attributes(schema_id)
        # TODO The below call works but smells fishy. What should we really be doing here?
        # Should/Can't we just obtain the dredential definition id from somewhere?
        # This should be written to the ledger already. Shouldn't this fail on trying
        # to write this again? However, this just returns the wanted cred_def_id.
        await write_credential_def(schema_id)

        # TODO Do we want to obtain cred_def_id from somewhere else
        cred_def_id = await get_cred_def_id(credential_def)
        credential_attributes = [
            {"name": k, "value": v} for k, v in list(zip(schema_attr, credential_attrs))
        ]
        record = await issue_credential(
            connection_id, schema_id, cred_def_id, credential_attributes
        )
        await aries_agent_controller.terminate()
        # TODO Do we want to return the record or just success?
        return record
    except Exception as e:
        await aries_agent_controller.terminate()
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
async def create_connection():
    """
    Creates invitation for the holder to scan

    Returns:
        QRCode PNG file from StreamingResponse
    """
    try:
        aries_agent_controller = aries_cloudcontroller.AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=admin_api_key,
            is_multitenant=is_multitenant,
        )

        invite = await aries_agent_controller.connections.create_invitation()
        # connection_id = invite["connection_id"]
        inviteURL = invite["invitation_url"]

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(inviteURL)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        buffer_img = io.BytesIO()
        img.save(buffer_img, format="PNG")
        await aries_agent_controller.terminate()
        # Alternatively, one can also return the QR code as a
        # base64 encoded string if that is prefered:
        #
        # img_64 = base64.b64encode(buffer_img.getvalue())
        # await aries_agent_controller.terminate()
        # payload = {"mime": "image/png", "image": img_64, "some_other_data": None}
        # return payload
        #
        # ! Make sure you have imported base64
        resp_img = io.BytesIO(buffer_img.getvalue())
        return StreamingResponse(resp_img, media_type="image/png")
    except Exception as e:
        await aries_agent_controller.terminate()
        raise e


# TODO Decide where this endpoint to lie


@router.get("/get-connection-id", tags=["connection"])
async def get_connection_id():
    try:
        aries_agent_controller = aries_cloudcontroller.AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=admin_api_key,
            is_multitenant=True,
        )
        connection = await get_connection_id()
        await aries_agent_controller.terminate()
        return connection
    except Exception as e:
        await aries_agent_controller.terminate()
        raise e
