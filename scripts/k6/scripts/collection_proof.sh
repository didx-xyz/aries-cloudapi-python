#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=10
  export ITERATIONS=10
  export ISSUER_PREFIX="k6_issuer_proof"
  export HOLDER_PREFIX="k6_holder_proof"
}

init() {
    run_test ./scenarios/create-holders.js
    run_test ./scenarios/create-invitation.js
    run_test ./scenarios/create-credentials.js
}

scenario() {
    run_test ./scenarios/create-proof.js
}

cleanup() {
    echo "Cleaning up..."
    local iterations=$((INITIAL_ITERATIONS * INTIAL_VUS))
    local vus=1
    xk6 run ./scenarios/delete-holders.js -e ITERATIONS=${iterations} -e VUS=${vus}
    xk6 run ./scenarios/delete-issuers.js -e ITERATIONS=1 -e VUS=1
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario
  cleanup
}
