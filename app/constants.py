import os

GOVERNANCE_AGENT_URL = os.getenv("ACAPY_GOVERNANCE_AGENT_URL", "http://localhost:3021")
GOVERNANCE_AGENT_API_KEY = os.getenv("ACAPY_GOVERNANCE_AGENT_API_KEY", "adminApiKey")

ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
ECOSYSTEM_AGENT_API_KEY = os.getenv("ACAPY_ECOSYSTEM_AGENT_API_KEY", "adminApiKey")

MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_API_KEY = os.getenv("ACAPY_MEMBER_AGENT_API_KEY", "adminApiKey")

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", "http://localhost:8001")

WEBHOOKS_URL = os.getenv("WEBHOOK_URL", "http://webhooks-web:3010")
