import os

YOMA_AGENT_URL = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
YOMA_AGENT_API_KEY = os.getenv("ACAPY_YOMA_AGENT_API_KEY", "adminApiKey")

ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
ECOSYSTEM_AGENT_API_KEY = os.getenv("ACAPY_ECOSYSTEM_AGENT_API_KEY", "adminApiKey")

MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_API_KEY = os.getenv("ACAPY_MEMBER_AGENT_API_KEY", "adminApiKey")

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", "http://localhost:8001")

WEBHOOKS_URL = os.getenv("WEBHOOKS_URL", "http://localhost:3010")

ACAPY_MULTITENANT_JWT_SECRET = os.getenv("ACAPY_MULTITENANT_JWT_SECRET", "jwtSecret")
ACAPY_ENDORSER_ALIAS = os.getenv("ACAPY_ENDORSER_ALIAS", "endorser")
