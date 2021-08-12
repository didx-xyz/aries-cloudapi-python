#!/bin/bash

# Sleep 10 hack to wait for von network nodes to start up
sleep 10

aca-py start \
    -it http '0.0.0.0' "$HTTP_PORT" \
    -e "$AGENT_ENDPOINT" "${AGENT_ENDPOINT/http/ws}" \
    "$@"
