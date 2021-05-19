from fastapi import APIRouter, HTTPException

import aries_cloudcontroller

router = APIRouter()


@router.get("/governance/ecosystem/policies", tags=["governance", "policies"])
async def schema_define():
    """
    Get the ecosystems policies

    Returns:
    --------
    ecosystem_policy: [dict]
        A list of json objects. One per policy
    """
    aries_agent_controller = aries_cloudcontroller.AriesAgentController(
        admin_url=f"http://multitenant-agent:3021",
        api_key="adminApiKey",
        is_multitenant=True,
    )

    await aries_agent_controller.terminate()
    pass
