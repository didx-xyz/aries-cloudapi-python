from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from . import schema
import qrcode
import aries_cloudcontroller
import IPython 
import io
from starlette.responses import FileResponse
router = APIRouter()

@router.post("/issuer/issue-credential",tags=["issue","credential"])
async def issue_credential(schema_id: str, connection_id: str, credential_attrs: List[str] = Query(None)):
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
        record = await aries_agent_controller.issuer.send_credential(connection_id, schema_id, cred_def_id, credential_attributes, trace=False)
        await aries_agent_controller.terminate()
        # TODO Do we want to return the record or just success?
        return record
        # for item in schema_attr:
    except Exception as e:
        pass


@router.get("/issuer/connection",tags=["connection", "wallets"])
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
        connection_id = invite["connection_id"]
        inviteURL = invite['invitation_url']
    

        qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=5)
        qr.add_data(inviteURL)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        img.save('./issuer_invite_QRcode.png')
        
    #     # content =  img.write()
        img.seek(0)
        await aries_agent_controller.terminate()
      
        return FileResponse('./issuer_invite_QRcode.png')
        # return StreamingResponse(io.BytesIO(img.tobytes()), media_type="image/png")
    #     # return inviteURL
      
        
    except Exception as e:
        pass    

    