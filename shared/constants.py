import os

host = "localhost"
url = f"http://{host}"
adminApiKey = "adminApiKey"

# the ACAPY_LABEL field with which the governance agent is initialised
GOVERNANCE_LABEL = os.getenv("GOVERNANCE_ACAPY_LABEL", "Governance").lower()

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


WEBHOOKS_URL = os.getenv("WEBHOOKS_URL", f"{url}:3010")
WEBHOOKS_PUBSUB_URL = os.getenv("WEBHOOKS_PUBSUB_URL", f"ws://{host}:3010/pubsub")

ACAPY_MULTITENANT_JWT_SECRET = os.getenv("ACAPY_MULTITENANT_JWT_SECRET", "jwtSecret")
ACAPY_ENDORSER_ALIAS = os.getenv("ACAPY_ENDORSER_ALIAS", "endorser")

ACAPY_TAILS_SERVER_BASE_URL = os.getenv("ACAPY_TAILS_SERVER_BASE_URL", f"{url}:6543")

# For testing ledger
LEDGER_TYPE: str = "von"
LEDGER_REGISTRATION_URL = os.getenv("LEDGER_REGISTRATION_URL", f"{url}:9000/register")

# Sse manager
MAX_EVENT_AGE_SECONDS = float(os.getenv("MAX_EVENT_AGE_SECONDS", "30"))
MAX_QUEUE_SIZE = int(os.getenv("MAX_QUEUE_SIZE", "200"))
QUEUE_CLEANUP_PERIOD = int(os.getenv("QUEUE_CLEANUP_PERIOD", "60"))
CLIENT_QUEUE_POLL_PERIOD = float(os.getenv("CLIENT_QUEUE_POLL_PERIOD", "0.2"))

# Sse
SSE_TIMEOUT = int(
    os.getenv("SSE_TIMEOUT", "150")
)  # maximum duration of an SSE connection
QUEUE_POLL_PERIOD = float(
    os.getenv("QUEUE_POLL_PERIOD", "0.1")
)  # period in seconds to retry reading empty queues
DISCONNECT_CHECK_PERIOD = float(
    os.getenv("DISCONNECT_CHECK_PERIOD", "0.2")
)  # period in seconds to check for disconnection

# client.py
TEST_CLIENT_TIMEOUT = int(os.getenv("TEST_CLIENT_TIMEOUT", "300"))
MAX_NUM_RETRIES = int(os.getenv("MAX_NUM_RETRIES", "3"))

# timeout for waiting for registries to be created
REGISTRY_CREATION_TIMEOUT = int(os.getenv("REGISTRY_CREATION_TIMEOUT", "60"))


LAGO_URL = os.getenv(
    "LAGO_URL", "http://192.168.0.186:3000/api/v1/events"
)  # use pc ip address
LAGO_API_KEY = os.getenv("LAGO_API_KEY", "")
# cb131628-c605-49bd-8aa3-93fe0289e1a3
