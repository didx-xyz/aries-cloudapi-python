#!/bin/bash
# Script to run tests and handle signals gracefully

# Trap SIGTERM and SIGINT to allow graceful shutdown
trap 'kill -TERM $PID' TERM INT

# Run pytest with all arguments passed to this script
pytest "$@" | tee /mnt/test_coverage.txt &

PID=$!
wait $PID
trap - TERM INT
wait $PID
EXIT_STATUS=$?
exit $EXIT_STATUS
