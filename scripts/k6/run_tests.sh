#!/bin/sh

source ./env.sh

run_test() {
    xk6 run -e SKIP_DELETE_ISSUERS="$1" -e SKIP_DELETE_HOLDERS="$2" "$3"
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Test $3 failed with exit code $exit_code"
        echo "Deleting Holders"
        xk6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=false ./scenarios/delete-holders.js
        echo "Exiting with exit code $exit_code ..."
        exit $exit_code
    fi
}

run_test true true ./scenarios/create-holders.js
run_test true true ./scenarios/create-invitation.js
run_test true true ./scenarios/create-credentials.js
run_test true true ./scenarios/create-proof.js
run_test false true ./scenarios/revoke-credentials.js
run_test true false ./scenarios/delete-holders.js

run_test false true ./scenarios/create-issuers.js

echo "All tests completed successfully"

# TODO: Better logic to handle deleting issuers and holders
