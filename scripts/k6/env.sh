#!/bin/bash
# Source secret if it exists
if [ -f "./.env.local" ]; then
    source ./.env.local
fi

export K6_STATSD_ENABLE_TAGS=true
export SKIP_DELETE_ISSUERS=true
export VUS=5
export ITERATIONS=5
export ISSUER_PREFIX=k6_issuer_dev1
export HOLDER_PREFIX=k6_holder_dev
export SCHEMA_NAME="proof_of_person"
export SCHEMA_VERSION="0.1.0"
