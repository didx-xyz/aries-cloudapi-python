from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HttpException

import os
from typing import Optional

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


async def create_controller(req_header: Optional[str] = Header(None)):
    try:
        if req_header["wallet_id"] and req_header["tenant_jwt"]:
            controller = AriesTenantController(
                req_header["wallet_id"], req_header["tenant_jwt"]
            )
        elif req_header["api_key"]:
            controller = AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=req_header["api_key"],
                is_multitenant=is_multitenant,
            )
        else:
            raise HttpException(
                status_code=400,
                detail="Bad headers. Either provide and api_key or both wallet_id and tenant_jwt",
            )
        return controller
    except Exception as e:
        raise e
