import os

GOVERNANCE_AGENT_URL = os.getenv("ACAPY_GOVERNANCE_AGENT_URL", "http://localhost:3021")
GOVERNANCE_AGENT_API_KEY = os.getenv("ACAPY_GOVERNANCE_AGENT_API_KEY", "adminApiKey")

TRUST_REGISTRY_URL = os.getenv("TRUST_REGISTRY_URL", "http://localhost:8001")

WEBHOOKS_PUBSUB_URL = os.getenv("WEBHOOKS_PUBSUB_URL", "ws://localhost:3010/pubsub")
