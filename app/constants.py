import os

GOVERNANCE_AGENT_URL = os.getenv("ACAPY_GOVERNANCE_AGENT_URL", "http://localhost:3021")
MULTITENANT_AGENT_URL = os.getenv("ACAPY_TENANT_AGENT_URL", "http://localhost:4021")
GOVERNANCE_AGENT_API_KEY = os.getenv("ACAPY_GOVERNANCE_AGENT_API_KEY", "adminApiKey")

TENANT_AGENT_URL = os.getenv("ACAPY_TENANT_AGENT_URL", "http://localhost:4021")
TENANT_AGENT_API_KEY = os.getenv("ACAPY_TENANT_AGENT_API_KEY", "adminApiKey")

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", "http://localhost:8001")

WEBHOOKS_URL = os.getenv("WEBHOOKS_URL", "http://localhost:3010")

ACAPY_MULTITENANT_JWT_SECRET = os.getenv("ACAPY_MULTITENANT_JWT_SECRET", "jwtSecret")
ACAPY_ENDORSER_ALIAS = os.getenv("ACAPY_ENDORSER_ALIAS", "endorser")
