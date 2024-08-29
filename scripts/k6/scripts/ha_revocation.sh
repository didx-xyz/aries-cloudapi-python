#!/bin/bash

# Source the configuration file
source ./env.sh
source "$(dirname "$0")/config.sh"

run_test() {
    local test_script="$1"
    xk6 run "$test_script"
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Test $test_script failed with exit code $exit_code"
        cleanup
        exit $exit_code
    fi
}

cleanup() {
    echo "Cleaning up..."
    export ITERATIONS=$((ITERATIONS * VUS)) # revoke sequentially
    export VUS=1
    xk6 run ./scenarios/delete-holders.js
    export ITERATIONS=1
    export VUS=1
    xk6 run ./scenarios/delete-issuers.js
}

init() {
    run_test ./scenarios/create-holders.js
    run_test ./scenarios/create-invitation.js
    run_test ./scenarios/create-credentials.js
    run_test ./scenarios/create-proof.js
}

run_scenarios_in_background() {
    export ITERATIONS=$((ITERATIONS * VUS)) # revoke sequentially
    export VUS=1
    xk6 run ./scenarios/revoke-credentials.js
    local revoke_exit=$?
    if [ $revoke_exit -ne 0 ]; then
        echo "revoke-credentials.js failed with exit code $revoke_exit"
        return $revoke_exit
    fi
    export IS_REVOKED=true
    export VUS=$INTIAL_VUS
    export ITERATIONS=$INITIAL_ITERATIONS
    xk6 run ./scenarios/create-proof.js
    local proof_exit=$?
    if [ $proof_exit -ne 0 ]; then
        echo "create-proof.js failed with exit code $proof_exit"
        return $proof_exit
    fi
    return 0
}

ha_tests() {
    local test_stack="$1"
    for ((i=1; i<=$HA_TEST_ITERATIONS; i++)); do
        echo "Starting HA test iteration $i of $HA_TEST_ITERATIONS for stack: $test_stack"
        run_scenarios_in_background &
        SCENARIOS_PID=$!

        # Associative array to store deployment PIDs
        declare -A DEPLOYMENT_PIDS

        # Start all deployments concurrently and store PIDs
        for DEPLOYMENT in $test_stack; do
            echo "Restarting deployment: $DEPLOYMENT"
            kubectl -n "$NAMESPACE" rollout restart deployment "$DEPLOYMENT"
            kubectl -n "$NAMESPACE" rollout status deployment "$DEPLOYMENT" &
            DEPLOYMENT_PIDS[$DEPLOYMENT]=$!
        done

        # Wait for all deployments to be restarted
        for DEPLOYMENT in $test_stack; do
            echo "Waiting for deployment: $DEPLOYMENT (PID: ${DEPLOYMENT_PIDS[$DEPLOYMENT]})"
            if [ -n "${DEPLOYMENT_PIDS[$DEPLOYMENT]}" ]; then
                wait "${DEPLOYMENT_PIDS[$DEPLOYMENT]}"
                if [ $? -ne 0 ]; then
                    echo "Deployment $DEPLOYMENT failed to restart"
                    kill $SCENARIOS_PID
                    cleanup
                    exit 1
                fi
            else
                echo "Warning: No PID found for ${DEPLOYMENT}"
            fi
        done

        # Start all deployments concurrently again and store PIDs
        for DEPLOYMENT in $test_stack; do
            echo "Restarting deployment: $DEPLOYMENT"
            kubectl -n "$NAMESPACE" rollout restart deployment "$DEPLOYMENT"
            kubectl -n "$NAMESPACE" rollout status deployment "$DEPLOYMENT" &
            DEPLOYMENT_PIDS[$DEPLOYMENT]=$!
        done

        # Wait for all deployments to be restarted again
        for DEPLOYMENT in $test_stack; do
            echo "Waiting for deployment: $DEPLOYMENT (PID: ${DEPLOYMENT_PIDS[$DEPLOYMENT]})"
            if [ -n "${DEPLOYMENT_PIDS[$DEPLOYMENT]}" ]; then
                wait "${DEPLOYMENT_PIDS[$DEPLOYMENT]}"
                if [ $? -ne 0 ]; then
                    echo "Deployment $DEPLOYMENT failed to restart"
                    kill $SCENARIOS_PID
                    cleanup
                    exit 1
                fi
            else
                echo "Warning: No PID found for ${DEPLOYMENT}"
            fi
        done

        echo "Waiting for scenarios to complete (PID: $SCENARIOS_PID)..."
        wait $SCENARIOS_PID
        SCENARIOS_EXIT=$?
        if [ $SCENARIOS_EXIT -ne 0 ]; then
            echo "Scenarios failed for stack $test_stack with exit code $SCENARIOS_EXIT"
            cleanup
            exit 1
        fi
        echo "Completed tests for stack: $test_stack"
    done
}

main() {
    init

    STACK=$1
    case $STACK in
        WEBS|AGENT|SERVICE|AUTH)
            ha_tests "${!STACK}"
            ;;
        ALL)
            ha_tests "$ALL"
            ;;
        *)
            echo "Invalid stack specified: $STACK"
            exit 1
            ;;
    esac

    cleanup
}

main "$@"
