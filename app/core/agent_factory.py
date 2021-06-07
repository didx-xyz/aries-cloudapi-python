from distutils.util import strtobool

import os

import aries_cloudcontroller

admin_url = os.getenv("ACAPY_ADMIN_URL")
admin_port = os.getenv("ACAPY_ADMIN_PORT")
admin_api_key = os.getenv("ACAPY_ADMIN_API_KEY")
is_multitenant = strtobool(os.getenv("IS_MULTITENANT", "False"))


def create_aries_agentcontroller():
    return aries_cloudcontroller.AriesAgentController(
            admin_url=f"{admin_url}:{admin_port}",
            api_key=admin_api_key,
            is_multitenant=is_multitenant,
    )
