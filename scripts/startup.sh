#!/bin/bash

# Sleep 15 hack to wait for von network nodes to start up
sleep 15

aca-py start \
    -it http '0.0.0.0' "$HTTP_PORT" \
    -e "$AGENT_ENDPOINT" "${AGENT_ENDPOINT/http/ws}" \
    "$@"
