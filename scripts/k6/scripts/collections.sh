#!/bin/bash

### DEFAULT ###

default_cleanup() {
    cleanup
}

#################

### REVOCATION ###
revocation_collection() {
    # This is the default collection
    INIT_FUNC="revocation_init"
    SCENARIO_FUNC="revocation_scenario"
    CLEANUP_FUNC="default_cleanup"
}

revocation_init() {
    run_test ./scenarios/create-holders.js
    run_test ./scenarios/create-invitation.js
    run_test ./scenarios/create-credentials.js
    run_test ./scenarios/create-proof.js
}

revocation_scenario() {
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

#################

### PROOFS ###

proof_collection() {
    # This collection only runs the proof scenario
    INIT_FUNC="proof_init"
    SCENARIO_FUNC="proof_scenario"
    CLEANUP_FUNC="default_cleanup"
}

proof_init() {
    run_test ./scenarios/create-holders.js
    run_test ./scenarios/create-invitation.js
    run_test ./scenarios/create-credentials.js
}

proof_scenario() {
    run_test ./scenarios/create-proof.js
    local proof_exit=$?
    if [ $proof_exit -ne 0 ]; then
        echo "create-proof.js failed with exit code $proof_exit"
        return $proof_exit
    fi
    return 0
}

#################
