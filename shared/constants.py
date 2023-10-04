import os

host = "localhost"
url = f"http://{host}"
adminApiKey = "adminApiKey"


GOVERNANCE_AGENT_URL = os.getenv("ACAPY_GOVERNANCE_AGENT_URL", f"{url}:3021")
GOVERNANCE_AGENT_API_KEY = os.getenv("ACAPY_GOVERNANCE_AGENT_API_KEY", adminApiKey)

GOVERNANCE_FASTAPI_ENDPOINT = os.getenv("GOVERNANCE_FASTAPI_ENDPOINT", f"{url}:8100")
GOVERNANCE_ACAPY_API_KEY = os.getenv("GOVERNANCE_ACAPY_API_KEY", adminApiKey)

TENANT_FASTAPI_ENDPOINT = os.getenv("TENANT_FASTAPI_ENDPOINT", f"{url}:8100")
TENANT_ACAPY_API_KEY = os.getenv("TENANT_ACAPY_API_KEY", adminApiKey)

TENANT_AGENT_URL = os.getenv("ACAPY_TENANT_AGENT_URL", f"{url}:4021")
TENANT_AGENT_API_KEY = os.getenv("ACAPY_TENANT_AGENT_API_KEY", adminApiKey)

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", f"{url}:8001")

WEBHOOKS_URL = os.getenv("WEBHOOKS_URL", f"{url}:3010")
WEBHOOKS_PUBSUB_URL = os.getenv("WEBHOOKS_PUBSUB_URL", f"ws://{host}:3010/pubsub")

ACAPY_MULTITENANT_JWT_SECRET = os.getenv("ACAPY_MULTITENANT_JWT_SECRET", "jwtSecret")
ACAPY_ENDORSER_ALIAS = os.getenv("ACAPY_ENDORSER_ALIAS", "endorser")

CLOUDAPI_URL = os.getenv("CLOUDAPI_URL", f"{url}:8100")
ACAPY_TAILS_SERVER_BASE_URL = os.getenv("ACAPY_TAILS_SERVER_BASE_URL", f"{url}:6543")

# For testing ledger
LEDGER_TYPE: str = "von"
LEDGER_REGISTRATION_URL = os.getenv("LEDGER_REGISTRATION_URL", f"{url}:9000/register")

# Sse manager
MAX_EVENT_AGE_SECONDS = int(os.getenv("MAX_EVENT_AGE_SECONDS", "30"))
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
