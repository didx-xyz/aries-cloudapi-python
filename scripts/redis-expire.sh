#!/bin/bash

# Redis connection details
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Debug flag
DEBUG=${DEBUG:-false}

# Function to get cluster nodes information
get_master_node() {
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls -a "$REDIS_PASSWORD" CLUSTER NODES 2>/dev/null | grep master | head -n 1 | cut -d' ' -f2 | cut -d@ -f1
}

# Function to process keys in batches
process_keys() {
    local master_node=$1
    local host=$(echo $master_node | cut -d: -f1)
    local port=$(echo $master_node | cut -d: -f2)
    local cursor=0
    local total_processed=0
    local batch_size=100

    while true; do
        # Get a batch of keys
        result=$(redis-cli -h "$host" -p "$port" --tls -a "$REDIS_PASSWORD" SCAN $cursor MATCH cloudapi:* COUNT 1000 2>/dev/null)
        cursor=$(echo "$result" | head -n 1)
        keys=$(echo "$result" | tail -n +2)

        # Prepare batch command
        commands=""
        for key in $keys; do
            commands+="EXPIRE $key 1\n"
            if $DEBUG; then
                echo "Adding command: EXPIRE $key 1"
            fi
            ((total_processed++))
        done

        # Execute batch if not empty
        if [ ! -z "$commands" ]; then
            if $DEBUG; then
                echo "Executing batch commands:"
                echo -e "$commands"
            fi
            result=$(echo -e "$commands" | redis-cli -h "$host" -p "$port" --tls -a "$REDIS_PASSWORD" --pipe 2>/dev/null)

            if $DEBUG; then
                echo "Detailed batch result:"
                echo "$result"
            fi
        fi

        if [ "$cursor" == "0" ]; then
            break
        fi
    done

    echo "Total keys processed: $total_processed"
}

echo "Starting Redis key expiration process..."

# Get a master node from the cluster
master_node=$(get_master_node)
if [ -z "$master_node" ]; then
    echo "Error: No master node found. Exiting."
    exit 1
fi

echo "Using master node: $master_node"

if $DEBUG; then
    echo "Debug mode is ON"
    echo "Redis Host: $REDIS_HOST"
    echo "Redis Port: $REDIS_PORT"
    echo "Listing all keys matching pattern 'cloudapi:*':"
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls -a "$REDIS_PASSWORD" --scan --pattern 'cloudapi:*' 2>/dev/null
fi

process_keys "$master_node"

echo "Redis key expiration process completed."
