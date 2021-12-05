import os

YOMA_AGENT_URL = os.getenv("ACAPY_YOMA_AGENT_URL", "http://localhost:3021")
ECOSYSTEM_AGENT_URL = os.getenv("ACAPY_ECOSYSTEM_AGENT_URL", "http://localhost:4021")
MEMBER_AGENT_URL = os.getenv("ACAPY_MEMBER_AGENT_URL", "http://localhost:4021")

EMBEDDED_API_KEY = os.getenv("EMBEDDED_API_KEY", "adminApiKey")

LEDGER_URL = os.getenv("LEDGER_NETWORK_URL", "http://localhost:9000/register")
LEDGER_TYPE = os.getenv("LEDGER_TYPE", "von")
