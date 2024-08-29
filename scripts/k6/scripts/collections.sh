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
}

revocation_config() {
    export VUS=10
    export ITERATIONS=5
    export ISSUER_PREFIX="k6_issuer_revocation"
    export HOLDER_PREFIX="k6_holder_revocation"
    export HOLDER_PREFIX="k6_holder_revocation"
    config
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
}

proof_config() {
    export VUS=10
    export ITERATIONS=10
    export ISSUER_PREFIX="k6_issuer_proof"
    export HOLDER_PREFIX="k6_holder_proof"
    config
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
    CONFIG_FUNC="schema_config"
}

schema_config() {
    export VUS=20
    export ITERATIONS=25
    export SCHEMA_PREFIX="k6_schema"
    config
}

schema_scenario() {
    run_test ./scenarios/create-schemas.js
}

schema_cleanup() {
    echo "No cleanup specified for schema collection"
}
#################

### CREATE ISSUERS ###
issuer_collection() {
    INIT_FUNC="default_init"
    SCENARIO_FUNC="issuers_scenario"
    CLEANUP_FUNC="issuers_cleanup"
    CONFIG_FUNC="issuers_config"
}

issuers_config() {
    export VUS=15
    export ITERATIONS=10
    export ISSUER_PREFIX="k6_issuer_issuer"
    config
}

issuers_scenario() {
    run_test ./scenarios/create-issuers.js
}

issuers_cleanup() {
    echo "Cleaning up..."
    export ITERATIONS=$((INITIAL_ITERATIONS * INTIAL_VUS))
    export VUS=1
    xk6 run ./scenarios/delete-issuers.js
}
#################

### CREATE CREDDEF ###
creddef_collection() {
    INIT_FUNC="creddef_init"
    SCENARIO_FUNC="creddef_scenario"
    CLEANUP_FUNC="issuers_cleanup"
    CONFIG_FUNC="creddef_config"
}

creddef_config() {
    export VUS=5 # setting any higher will exceed 30s lifecyce pre-stop on tenant-web
    export ITERATIONS=8
    export ISSUER_PREFIX="k6_issuer_creddef"
    config
}

creddef_init() {
    run_test ./scenarios/create-issuers.js
}

creddef_scenario() {
    run_test ./scenarios/create-creddef.js
}
#################
