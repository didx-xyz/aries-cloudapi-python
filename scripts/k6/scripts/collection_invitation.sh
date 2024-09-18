#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
    export VUS=5
    export ITERATIONS=50
    export HOLDER_PREFIX="k6_holder_invitation"
    export ISSUER_PREFIX="k6_issuer_invitation"
    export NUM_ISSUERS=1
}

init() {
  log "Initializing..."
  xk6 run ./scenarios/bootstrap-issuer.js -e ITERATIONS=1 -e VUS=1
  xk6 run ./scenarios/create-holders.js
}

scenario() {
    log "Running scenario..."
    run_test ./scenarios/create-invitations.js
}

cleanup() {
  log "Cleaning up..."
  xk6 run ./scenarios/delete-holders.js
  xk6 run ./scenarios/delete-issuers.js -e ITERATIONS="${NUM_ISSUERS}" -e VUS=1
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario
  cleanup
}
