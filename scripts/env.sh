# ./app/constants.py
export ACAPY_GOVERNANCE_AGENT_URL="https://governance-ga-agent.cloudapi.dev.didxtech.com"
export ACAPY_TENANT_AGENT_URL="https://governance-mt-agent.cloudapi.dev.didxtech.com"
export ACAPY_GOVERNANCE_AGENT_API_KEY=$(kubectl -n dev-cloudapi get secret ga-and-mt-web-env -o jsonpath='{.data.ACAPY_GOVERNANCE_AGENT_API_KEY}' | base64 -d)

export ACAPY_TENANT_AGENT_API_KEY=$(kubectl -n dev-cloudapi get secret ga-and-mt-web-env -o jsonpath='{.data.ACAPY_TENANT_AGENT_API_KEY}' | base64 -d)

export TRUST_REGISTRY_URL="https://trust-registry.cloudapi.dev.didxtech.com"

export WEBHOOKS_URL="https://webhooks.cloudapi.dev.didxtech.com"

export ACAPY_MULTITENANT_JWT_SECRET=$(kubectl -n dev-cloudapi get secret ga-and-mt-web-env -o jsonpath='{.data.ACAPY_MULTITENANT_JWT_SECRET}' | base64 -d)
export ACAPY_TAILS_SERVER_BASE_URL="https://tails-server.cloudapi.dev.didxtech.com"
export CLOUDAPI_URL="https://cloudapi.dev.didxtech.com"

# ./app/tests/util/constants.py
export GOVERNANCE_FASTAPI_ENDPOINT="https://cloudapi.dev.didxtech.com"
export GOVERNANCE_ACAPY_API_KEY=$(kubectl -n dev-cloudapi get secret ga-and-mt-web-env -o jsonpath='{.data.ACAPY_GOVERNANCE_AGENT_API_KEY}' | base64 -d)
export TENANT_FASTAPI_ENDPOINT="https://cloudapi.dev.didxtech.com"
export TENANT_ACAPY_API_KEY=$(kubectl -n dev-cloudapi get secret ga-and-mt-web-env -o jsonpath='{.data.ACAPY_TENANT_AGENT_API_KEY}' | base64 -d)
export LEDGER_REGISTRATION_URL="https://ledger-browser.cloudapi.dev.didxtech.com/register"
export WEBHOOKS_URL="https://webhooks.cloudapi.dev.didxtech.com"
