import os

host = "localhost"
url = f"http://{host}"
adminApiKey = "adminApiKey"

# pylint: disable=invalid-name

PROJECT_VERSION = os.getenv("PROJECT_VERSION", "1.0.0")

# the ACAPY_LABEL field with which the governance agent is initialised
GOVERNANCE_LABEL = os.getenv("GOVERNANCE_ACAPY_LABEL", "Governance")

GOVERNANCE_AGENT_URL = os.getenv("ACAPY_GOVERNANCE_AGENT_URL", f"{url}:3021")
GOVERNANCE_AGENT_API_KEY = os.getenv("ACAPY_GOVERNANCE_AGENT_API_KEY", adminApiKey)

GOVERNANCE_FASTAPI_ENDPOINT = os.getenv(
    "GOVERNANCE_FASTAPI_ENDPOINT", f"{url}:8200"
)  # governance-ga-web
GOVERNANCE_ACAPY_API_KEY = os.getenv("GOVERNANCE_ACAPY_API_KEY", adminApiKey)

TENANT_FASTAPI_ENDPOINT = os.getenv(
    "TENANT_FASTAPI_ENDPOINT", f"{url}:8300"
)  # governance-tenant-web
TENANT_ADMIN_FASTAPI_ENDPOINT = os.getenv(
    "TENANT_ADMIN_FASTAPI_ENDPOINT", f"{url}:8100"
)  # governance-multitenant-web
TENANT_ACAPY_API_KEY = os.getenv("TENANT_ACAPY_API_KEY", adminApiKey)

TENANT_AGENT_URL = os.getenv("ACAPY_TENANT_AGENT_URL", f"{url}:4021")
TENANT_AGENT_API_KEY = os.getenv("ACAPY_TENANT_AGENT_API_KEY", adminApiKey)

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", f"{url}:8001")
TRUST_REGISTRY_FASTAPI_ENDPOINT = os.getenv(
    "TRUST_REGISTRY_FASTAPI_ENDPOINT", f"{url}:8400"
)  # governance-trust-registry

WAYPOINT_URL = os.getenv("WAYPOINT_URL", f"{url}:3011")

ACAPY_MULTITENANT_JWT_SECRET = os.getenv("ACAPY_MULTITENANT_JWT_SECRET", "jwtSecret")
ACAPY_ENDORSER_ALIAS = os.getenv("ACAPY_ENDORSER_ALIAS", "endorser")

ACAPY_TAILS_SERVER_BASE_URL = os.getenv("ACAPY_TAILS_SERVER_BASE_URL", f"{url}:6543")

# For testing ledger
LEDGER_TYPE: str = "von"
LEDGER_REGISTRATION_URL = os.getenv("LEDGER_REGISTRATION_URL", f"{url}:9000/register")

# Sse
SSE_TIMEOUT = int(
    os.getenv("SSE_TIMEOUT", "60")
)  # maximum duration of an SSE connection
DISCONNECT_CHECK_PERIOD = float(
    os.getenv("DISCONNECT_CHECK_PERIOD", "0.2")
)  # period in seconds to check for disconnection

# client.py
TEST_CLIENT_TIMEOUT = int(os.getenv("TEST_CLIENT_TIMEOUT", "300"))
MAX_NUM_RETRIES = int(os.getenv("MAX_NUM_RETRIES", "3"))

# timeout for waiting for registries to be created
REGISTRY_CREATION_TIMEOUT = int(os.getenv("REGISTRY_CREATION_TIMEOUT", "60"))
REGISTRY_SIZE = int(os.getenv("REGISTRY_SIZE", "32767"))

# NATS
NATS_SERVER = os.getenv("NATS_SERVER", "nats://nats:4222")
NATS_SUBJECT = os.getenv("NATS_SUBJECT", "cloudapi.aries.events")
NATS_STREAM = os.getenv("NATS_STREAM", "cloudapi_aries_events")
NATS_CREDS_FILE = os.getenv("NATS_CREDS_FILE", "")
ENDORSER_DURABLE_CONSUMER = os.getenv("ENDORSER_DURABLE_CONSUMER", "endorser")
