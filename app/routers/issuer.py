from fastapi import APIRouter, HTTPException, Query
from typing import List
import base64
import io
from . import schema
import qrcode
import aries_cloudcontroller

router = APIRouter()


@router.get("/issuer/issue-credential", tags=["issue", "credential"])
async def issue_credential(
    schema_id: str, connection_id: str, credential_attrs: List[str] = Query(None)
):
    """
    Issues a credential
    """
    aries_agent_controller = aries_cloudcontroller.AriesAgentController(
        admin_url=f"http://multitenant-agent:3021",
        api_key="adminApiKey",
        is_multitenant=True,
    )
    try:
        schema_resp = await schema.get_by_id(schema_id)
        schema_attr = schema_resp["attrNames"]
        credential_attributes = dict(zip(schema_attr, credential_attrs))
        record = await aries_agent_controller.issuer.send_credential(
            connection_id, schema_id, cred_def_id, credential_attributes, trace=False
        )
        await aries_agent_controller.terminate()
        # TODO Do we want to return the record or just success?
        return record
        # for item in schema_attr:
    except Exception as e:
        pass


@router.get(
    "/issuer/connection",
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
    """
    aries_agent_controller = aries_cloudcontroller.AriesAgentController(
        admin_url=f"http://multitenant-agent:3021",
        api_key="adminApiKey",
        is_multitenant=True,
    )
    try:
        invite = await aries_agent_controller.connections.create_invitation()
        # connection_id = invite["connection_id"]
        inviteURL = invite["invitation_url"]

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(inviteURL)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        buffer_img = io.BytesIO()
        img.save(buffer_img, format="JPEG")
        img_64 = base64.b64encode(buffer_img.getvalue())
        await aries_agent_controller.terminate()
        payload = {"mime": "image/png", "image": img_64, "some_other_data": None}
        return payload
    except Exception as e:
        pass
