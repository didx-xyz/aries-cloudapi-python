#!/bin/bash

export NAMESPACE="dev-cloudapi"
export ISSUER_PREFIX="k6_issuer_debug"
export HOLDER_PREFIX="k6_holder_debug"
export INTIAL_VUS=5
export INITIAL_ITERATIONS=2
export VUS=$INTIAL_VUS
export ITERATIONS=$INITIAL_ITERATIONS
export WEBS="governance-ga-web governance-multitenant-web governance-tenant-web governance-public-web"
export AGENT="governance-ga-agent governance-multitenant-agent"
export SERVICE="governance-endorser tails-server governance-trust-registry waypoint"
export AUTH="inquisitor"
export INVALID="governance-webhooks-web"
export HA_TEST_ITERATIONS=1 # Configurable number of HA test iterations
export RESTART_ITERATIONS=1 # Configurable number of restart iterations
export NUM_ISSUERS=1

# Combine all stacks into one variable
ALL="$WEBS $AGENT $SERVICE $AUTH"
# Remove INVALID deployments from ALL
for invalid in $INVALID; do
    ALL=${ALL//$invalid/}
done
# Remove any extra spaces
ALL=$(echo "$ALL" | tr -s ' ')
export ALL
