from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from . import schema

import aries_cloudcontroller

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
