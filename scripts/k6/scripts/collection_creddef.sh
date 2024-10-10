#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=5 # setting any higher will exceed 30s lifecyce pre-stop on tenant-web
  export ITERATIONS=8
  export ISSUER_PREFIX="k6_issuer_creddef"
}

init() {
  run_test ./scenarios/create-issuers.js
}

scenario() {
  run_test ./scenarios/create-creddef.js
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
