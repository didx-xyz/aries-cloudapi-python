#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=10
  export ITERATIONS=10
  export ISSUER_PREFIX="k6_issuer_issuer_ops"
  export HOLDER_PREFIX="k6_holder_issuer_ops"
}

init() {
  log "No init function specified"
}

scenario_create_issuers() {
  run_test ./scenarios/create-issuers.js
}

scenario_create_schemas() {
  export VUS=10
  export ITERATIONS=40
  export SCHEMA_PREFIX="k6_issuer_ops2"
  run_test ./scenarios/create-schemas.js
}

cleanup() {
  log "Cleaning up..."
  xk6 run ./scenarios/delete-issuers.js
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario_create_issuers
  run_ha_iterations "${deployments}" scenario_create_schemas

  cleanup
}
