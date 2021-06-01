from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException

import os
from typing import Optional

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


async def create_controller(req_header: Header):
    try:
        req_header = eval(req_header)
        if ("wallet_id" in req_header) and ("tenant_jwt" in req_header):
            controller = AriesTenantController(
                req_header["wallet_id"], req_header["tenant_jwt"]
            )
        elif "api_key" in req_header:
            controller = AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=req_header["api_key"],
                is_multitenant=is_multitenant,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Bad headers. Either provide and api_key or both wallet_id and tenant_jwt",
            )
        return controller
    except Exception as e:
        raise e
