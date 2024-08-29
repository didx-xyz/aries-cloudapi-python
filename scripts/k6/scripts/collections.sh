#!/bin/bash

### DEFAULT ###
default_cleanup() {
    cleanup
}

default_init() {
    echo "No init function specified"
}
#################

### REVOCATION ###
revocation_collection() {
    # This is the default collection
    INIT_FUNC="revocation_init"
    SCENARIO_FUNC="revocation_scenario"
    CLEANUP_FUNC="default_cleanup"

    export VUS=10
    export ITERATIONS=5
    export ISSUER_PREFIX="k6_issuer_revocation"
    export HOLDER_PREFIX="k6_holder_revocation"
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
    run_test ./scenarios/revoke-credentials.js
    export IS_REVOKED=true
    export VUS=$INTIAL_VUS
    export ITERATIONS=$INITIAL_ITERATIONS
    run_test ./scenarios/create-proof.js
}
#################

### PROOFS ###
proof_collection() {
    # This collection only runs the proof scenario
    INIT_FUNC="proof_init"
    SCENARIO_FUNC="proof_scenario"
    CLEANUP_FUNC="default_cleanup"

    export VUS=10
    export ITERATIONS=10
    export ISSUER_PREFIX="k6_issuer_proof"
    export HOLDER_PREFIX="k6_holder_proof"
}

proof_init() {
    run_test ./scenarios/create-holders.js
    run_test ./scenarios/create-invitation.js
    run_test ./scenarios/create-credentials.js
}

proof_scenario() {
    run_test ./scenarios/create-proof.js
}
#################

### CREATE SCHEMAS ###
schema_collection() {
    # This collection only runs the create-schema scenario
    INIT_FUNC="default_init"
    SCENARIO_FUNC="schema_scenario"
    CLEANUP_FUNC="schema_cleanup"

    export VUS=20
    export ITERATIONS=25
    export SCHEMA_PREFIX="k6_schema"
}

schema_scenario() {
    run_test ./scenarios/create-schemas.js
}

schema_cleanup() {
    echo "No cleanup specified for schema collection"
}
#################
