#!/bin/bash

# Redis connection details
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

# Function to get all keys
get_all_keys() {
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls -a "$REDIS_PASSWORD" --scan --pattern '*'
}

# Function to expire keys in batches
expire_keys() {
    local batch_size=100
    local count=0
    local total_processed=0
    local commands=""

    while read -r key; do
        if [[ ! $key == lock:* ]]; then
            commands+="EXPIRE $key 60\n"
            ((count++))
            ((total_processed++))

            if ((count % batch_size == 0)); then
                echo -e "$commands" | redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls -a "$REDIS_PASSWORD" -x > /dev/null
                echo "Processed $total_processed keys..."
                commands=""
                count=0
            fi
        fi
    done

    # Process any remaining keys
    if [[ -n "$commands" ]]; then
        echo -e "$commands" | redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" --tls -a "$REDIS_PASSWORD" -x > /dev/null
        echo "Processed $total_processed keys..."
    fi

    echo "Total keys processed: $total_processed"
}

# Main script
echo "Starting Redis key expiration process..."
get_all_keys | expire_keys
echo "Redis key expiration process completed."
