#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=10
  export ITERATIONS=25
  export ISSUER_PREFIX="k6_issuer_credential_ops"
  export HOLDER_PREFIX="k6_holder_credential_ops"
  export NUM_ISSUERS=2
}

init() {
  xk6 run ./scenarios/bootstrap-issuer.js -e ITERATIONS=1 -e VUS=1
}

scenario_create_holders() {
  export SLEEP_DURATION=0.75
  local iterations=$((ITERATIONS * VUS))
  local vus=1
  xk6 run ./scenarios/create-holders.js -e ITERATIONS=${iterations} -e VUS=${vus}
}

senario_create_invitations() {
  run_test ./scenarios/create-invitations.js
}

scemario_create_credentials() {
  run_test ./scenarios/create-credentials.js
}

scenario_create_proof_verified() {
  run_test ./scenarios/create-proof.js
}

scenario_revoke_credentials() {
  local iterations=$((ITERATIONS * VUS))
  local vus=1
  xk6 run ./scenarios/revoke-credentials.js -e ITERATIONS=${iterations} -e VUS=${vus}
}

scenario_create_proof_unverified() {
  export IS_REVOKED=true
  run_test ./scenarios/create-proof.js
}

cleanup() {
  log "Cleaning up..."
  xk6 run ./scenarios/delete-holders.js
  # xk6 run ./scenarios/delete-issuers.js -e ITERATIONS="${NUM_ISSUERS}" -e VUS=1
}

run_collection() {
  local deployments="$1"

  config
  init
  run_ha_iterations "${deployments}" scenario_create_holders
  run_ha_iterations "${deployments}" senario_create_invitations
  run_ha_iterations "${deployments}" scemario_create_credentials
  run_ha_iterations "${deployments}" scenario_create_proof_verified
  run_ha_iterations "${deployments}" scenario_revoke_credentials
  run_ha_iterations "${deployments}" scenario_create_proof_unverified

  cleanup
}
