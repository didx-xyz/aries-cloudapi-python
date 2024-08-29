#!/bin/bash
# Source the configuration file
source ./env.sh
source "$(dirname "$0")/config.sh"
source "$(dirname "$0")/collections.sh"

DEPLOYMENTS=$1
COLLECTION=${2:-revocation}

config() {
    export INTIAL_VUS=$VUS
    export INITIAL_ITERATIONS=$ITERATIONS
}

run_test() {
    local test_script="$1"
    xk6 run "$test_script"
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Test $test_script failed with exit code $exit_code"
        $CLEANUP_FUNC
        exit 1
    fi
}

cleanup() {
    echo "Cleaning up..."
    export ITERATIONS=$((INITIAL_ITERATIONS * INTIAL_VUS))
    export VUS=1
    xk6 run ./scenarios/delete-holders.js
    export ITERATIONS=1
    export VUS=1
    xk6 run ./scenarios/delete-issuers.js
}

ha_tests() {
    local deployments="$1"
    for ((i=1; i<=$HA_TEST_ITERATIONS; i++)); do
        echo "Starting HA test iteration $i of $HA_TEST_ITERATIONS"
        $SCENARIO_FUNC &
        SCENARIOS_PID=$!

        for ((j=1; j<=2; j++)); do
            if [ -n "$deployments" ]; then
                # Array to store deployment PIDs
                DEPLOYMENT_PIDS=()

                # Start all deployments concurrently and store PIDs
                for DEPLOYMENT in $deployments; do
                    echo "Restarting deployment: $DEPLOYMENT"
                    kubectl -n "$NAMESPACE" rollout restart deployment "$DEPLOYMENT"
                    kubectl -n "$NAMESPACE" rollout status deployment "$DEPLOYMENT" &
                    DEPLOYMENT_PIDS+=($!)
                done

                # Wait for all deployments to be restarted
                for PID in "${DEPLOYMENT_PIDS[@]}"; do
                    wait $PID
                    if [ $? -ne 0 ]; then
                        echo "A deployment failed to restart"
                        kill $SCENARIOS_PID
                        exit 1
                    fi
                done
            else
                echo "No stack specified. Skipping restarts."
            fi
        done

        echo "Waiting for scenarios to complete (PID: $SCENARIOS_PID)..."
        wait $SCENARIOS_PID
        SCENARIOS_EXIT=$?
        if [ $SCENARIOS_EXIT -ne 0 ]; then
            echo "Scenarios failed with exit code $SCENARIOS_EXIT"
            exit 1
        fi
        echo "Completed tests for iteration $i"
    done
}

main() {
    # Load the specified collection
    if declare -f "${COLLECTION}_collection" > /dev/null; then
        ${COLLECTION}_collection
    else
        echo "Error: Unknown collection '${COLLECTION}'"
        exit 1
    fi
    $CONFIG_FUNC
    $INIT_FUNC
    ha_tests "$DEPLOYMENTS"
    $CLEANUP_FUNC
}

main "$@"
