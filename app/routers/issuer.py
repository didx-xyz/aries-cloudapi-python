from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List
import io
import qrcode
import aries_cloudcontroller
import os
import json
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
        schema_resp = await aries_agent_controller.schema.get_by_id(schema_id)
        print (schema_resp)
        schema_attr = schema_resp["schema"]["attrNames"]

        cred_def_id = schema_resp["schema"]["id"]  # I think this is wrong
        # cred_def_id = "Vq5u2ZsYr2cfLxPfA8rYRA:3:CL:217905:default"
        credential_attributes = list(dict(zip(schema_attr, credential_attrs)))
        credential_attributes = json.dumps(credential_attributes)
        print(credential_attributes)
        record = await aries_agent_controller.issuer.send_credential(
            connection_id, schema_id, cred_def_id, credential_attributes, trace=False
        )
        await aries_agent_controller.terminate()
        # TODO Do we want to return the record or just success?
        return record
        # for item in schema_attr:
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

#TODO Decide where this endpoint to lie

@router.get("/get-connection-id", tags=["connection"])

async def get_connection_id():
    try:
        aries_agent_controller = aries_cloudcontroller.AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=admin_api_key,
                is_multitenant=True,
        )
        connection = await aries_agent_controller.connections.get_connections()
        await aries_agent_controller.terminate()
        return connection
    except Exception as e:
        await aries_agent_controller.terminate()
        raise e

#TODO THis endpoint will definely be used in numerous place maybe make this as a util or something
#Currently using this endpoint solely for ease of testing
# @router.get("/check-active-conenction", tags=["connection"])
# async def check_active_connection(connection_id : str):
    
#     try:
#         aries_agent_controller = aries_cloudcontroller.AriesAgentController(
#                 admin_url=f"{admin_url}:{admin_port}",
#                 api_key=admin_api_key,
#                 is_multitenant=is_multitenant,
#         )
    
#         response = await agent_controller.connections.get_connections()
#         results = response['results']
#         print("Results : ", results)
#         print('\n')
#         if len(results) > 0:
#             connection = response['results'][0]
#             print("Connection :", connection)
#             if connection['state'] == 'active':
#                 connection_id = connection["connection_id"]
#                 print("\nActive Connection ID : ", connection_id)
#             else:
#                 print("\nNo active connection found - wait a bit and execute again")
