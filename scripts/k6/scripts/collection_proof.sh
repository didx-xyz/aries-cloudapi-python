#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=5
  export ITERATIONS=10
  export ISSUER_PREFIX="k6_issuer_proof"
  export HOLDER_PREFIX="k6_holder_proof"
}

init() {
    xk6 run ./scenarios/bootstrap-issuer.js -e ITERATIONS=1 -e VUS=1
    run_test ./scenarios/create-holders.js
    run_test ./scenarios/create-invitations.js
    run_test ./scenarios/create-credentials.js
}

scenario() {
    run_test ./scenarios/create-proof.js
}

cleanup() {
    log "Cleaning up..."
    xk6 run ./scenarios/delete-holders.js
    xk6 run ./scenarios/delete-issuers.js -e ITERATIONS=1 -e VUS=1
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario
  cleanup
}
