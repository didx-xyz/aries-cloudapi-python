#!/bin/sh

source ./env.sh

run_test() {
    xk6 run -e SKIP_DELETE_ISSUERS="$1" -e SKIP_DELETE_HOLDERS="$2" "$3"
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Test $3 failed with exit code $exit_code"
        echo "Deleting Holders"
        xk6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=false delete-holders.js
        echo "Exiting with exit code $exit_code ..."
        exit $exit_code
    fi
}

run_test true true create-holders.js
run_test true true create-invitation.js
run_test true true create-credentials.js
run_test true true create-proof.js
run_test false false delete-holders.js

echo "All tests completed successfully"
