#!/usr/bin/env bash

set -euo pipefail

# Source the configuration file
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

#------------------------------------------------------------------------------
# Declare functions
#------------------------------------------------------------------------------

# A function to print out error, log and warning messages along with other status information
# Copied from https://google-styleguide.googlecode.com/svn/trunk/shell.xml#STDOUT_vs_STDERR
err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: ERROR: $@" >&2
  exit
}

log() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: INFO: $@" >&1
}

wrn() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: WARNING: $@" >&1
}

run_test() {
  local test_script="$1"
  xk6 run "${test_script}"
  local exit_code=$?
  if [[ ${exit_code} -ne 0 ]]; then
    echo "Test ${test_script} failed with exit code ${exit_code}" >&2
    return 1
  fi
}

restart_deployment() {
  local deployment="$1"
  log "Restarting deployment: ${deployment}"
  kubectl -n "${NAMESPACE}" rollout restart deployment "${deployment}"
  kubectl -n "${NAMESPACE}" rollout status deployment "${deployment}"
}

run_ha_iterations() {
  local deployments="$1"
  local scenario_func="$2"

  for ((i=1; i<=HA_TEST_ITERATIONS; i++)); do
    log "Starting HA test iteration $i of ${HA_TEST_ITERATIONS}"

    ${scenario_func} &
    local scenario_pid=$!

    if [[ -n "${deployments}" ]]; then
      for ((j=1; j<=RESTART_ITERATIONS; j++)); do
        local deployment_pids=()
        for deployment in ${deployments}; do
          restart_deployment "${deployment}" &
          deployment_pids+=($!)
        done
        for pid in "${deployment_pids[@]}"; do
          wait "${pid}"
          if [[ $? -ne 0 ]]; then
            wrn "A deployment failed to restart" >&2
            kill "${scenario_pid}"
            return 1
          fi
        done
      done

        # Check if scenario is still running after deployments restart
        if kill -0 "${scenario_pid}" 2>/dev/null; then
            log "Scenario is still running after all deployments were restarted"
        else
            wrn "WARNING: Scenario completed too quickly, before all deployments were restarted"
        fi
    else
      log "No stack specified. Skipping restarts."
    fi

    wait "${scenario_pid}"
    if [[ $? -ne 0 ]]; then
      err "Scenarios failed with exit code $?" >&2
      return 1
    fi
    log "Completed tests for iteration $i"
  done
}
