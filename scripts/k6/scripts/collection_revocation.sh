#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=10
  export ITERATIONS=5
  export ISSUER_PREFIX="k6_issuer_revocation"
  export HOLDER_PREFIX="k6_holder_revocation"
  export NUM_ISSUERS=1
}

init() {
  xk6 run ./scenarios/bootstrap-issuer.js -e ITERATIONS=1 -e VUS=1
  run_test ./scenarios/create-holders.js
  run_test ./scenarios/create-invitations.js
  run_test ./scenarios/create-credentials.js
  run_test ./scenarios/create-proof.js
}

scenario() {
  local iterations=$((ITERATIONS * VUS))  # revoke sequentially
  local vus=1
  run_test ./scenarios/revoke-credentials.js -e INTERATIONS="${iterations}" -e VUS="${vus}"
  export IS_REVOKED=true
  run_test ./scenarios/create-proof.js
}

cleanup() {
  log "Cleaning up..."
  local iterations=$((ITERATIONS * VUS))
  local vus=1
  xk6 run ./scenarios/delete-holders.js -e ITERATIONS="${iterations}" -e VUS="${vus}"
  xk6 run ./scenarios/delete-issuers.js -e ITERATIONS="${NUM_ISSUERS}" -e VUS=1
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario
  cleanup
}
