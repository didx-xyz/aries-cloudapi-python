#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

config() {
  export VUS=40
  export ITERATIONS=250
  export ISSUER_PREFIX="k6_issuer_tmodelg"
  export HOLDER_PREFIX="k6_holder_tmodelg"
  export NUM_ISSUERS=2
}

init() {
  xk6 run --out statsd ./scenarios/bootstrap-issuer.js -e ITERATIONS=1 -e VUS=1
}

scenario_create_holders() {
  export SLEEP_DURATION=0.02
  # local iterations=$((ITERATIONS * VUS))
  # local vus=1
  # xk6 run ./scenarios/create-holders.js -e ITERATIONS=${iterations} -e VUS=${vus}
  xk6 run --out statsd ./scenarios/create-holders.js
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
  xk6 run --out statsd ./scenarios/revoke-credentials.js -e ITERATIONS=${iterations} -e VUS=${vus}
}

scenario_create_proof_unverified() {
  export IS_REVOKED=true
  run_test ./scenarios/create-proof.js
}

cleanup() {
  log "Cleaning up..."
  xk6 run --out statsd ./scenarios/delete-holders.js
  # xk6 run --out statsd ./scenarios/delete-issuers.js -e ITERATIONS="${NUM_ISSUERS}" -e VUS=1
}

run_collection() {
  local deployments="$1"

  config
  # init
  # scenario_create_holders
  # run_ha_iterations "${deployments}" senario_create_invitations
  # export VUS=25
  # export ITERATIONS=400
  # run_ha_iterations "${deployments}" scemario_create_credentials
  export VUS=40
  export ITERATIONS=250
  run_ha_iterations "${deployments}" scenario_create_proof_verified

  # cleanup
}
