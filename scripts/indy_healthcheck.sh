#!/bin/sh

# Create a unique pool name
POOL_NAME="health"

# Create a temp file name
CLI_TMP_FILE="/tmp/indy_healthcheck.txn"

# Write the commands to the temporary configuration file
echo "pool create $POOL_NAME gen_txn_file=/home/indy/ledger/sandbox/pool_transactions_genesis" > $CLI_TMP_FILE
echo "pool connect $POOL_NAME" >> $CLI_TMP_FILE
echo "pool refresh" >> $CLI_TMP_FILE
echo "pool disconnect" >> $CLI_TMP_FILE
echo "pool delete $POOL_NAME" >> $CLI_TMP_FILE
echo "exit" >> $CLI_TMP_FILE
NODES_STATUS=$(indy-cli $CLI_TMP_FILE 2>&1 | grep -P 'Pool\s+"\w+"\s+has been deleted.')
# Run indy-cli with the temporary configuration file and check if deleteion of pool was successful
# If the health check fails, exit with a non-zero status code
if ! echo "$NODES_STATUS" | grep -q "has been deleted"; then
  exit 1
fi

# If pool was successfully created and deleted, exit with a zero status code
exit 0