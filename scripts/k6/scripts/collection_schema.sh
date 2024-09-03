#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
    export VUS=20
    export ITERATIONS=25
    export SCHEMA_PREFIX="k6_schema"
}

init() {
    log "No init function specified"
}

scenario() {
    run_test ./scenarios/create-schemas.js
}

cleanup() {
    log "No cleanup specified for schema collection"
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario
  cleanup
}
