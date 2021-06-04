from aries_cloudcontroller import AriesAgentController, AriesTenantController
from fastapi import Header, HTTPException
from contextlib import asynccontextmanager

import os

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
is_multitenant = os.getenv("IS_MULTITENANT", False)


@asynccontextmanager
async def create_controller(req_header: Header):
    is_valid_header = req_header and (
        ("wallet_id" in req_header)
        and ("tenant_jwt" in req_header)
        or "api_key" in req_header
    )
    if is_valid_header:
        req_header = eval(req_header)
        if "api_key" in req_header:
            controller = AriesAgentController(
                admin_url=f"{admin_url}:{admin_port}",
                api_key=req_header["api_key"],
                is_multitenant=is_multitenant,
            )
        else:
            controller = AriesTenantController(
                req_header["wallet_id"], req_header["tenant_jwt"]
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Bad headers. Either provide an api_key or both wallet_id and tenant_jwt",
        )
    try:
        yield controller
    except Exception as e:
        raise e
    finally:
        await controller.terminate()
