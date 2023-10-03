#!/bin/bash
EXIT_CODE=0
COUNTER=0
PYTEST_COMMAND="$@"
while [[ $EXIT_CODE == 0 ]]; do
    $PYTEST_COMMAND
    EXIT_CODE=$?
    COUNTER=$((COUNTER+1))
    echo "Test run $COUNTER completed with exit code $EXIT_CODE"
done