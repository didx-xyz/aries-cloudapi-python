#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
    export VUS=15
    export ITERATIONS=10
    export ISSUER_PREFIX="k6_issuer_issuer"
}

init() {
  log "No init function specified"
}

scenario() {
    run_test ./scenarios/create-issuers.js
}

cleanup() {
    echo "Cleaning up..."
    export ITERATIONS=$((INITIAL_ITERATIONS * INTIAL_VUS))
    export VUS=1
    xk6 run ./scenarios/delete-issuers.js
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario
  cleanup
}
