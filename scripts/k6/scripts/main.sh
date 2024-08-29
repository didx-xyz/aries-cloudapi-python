#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/collections.sh"

usage() {
    echo "Usage: $0 [-s STACK] [-c COLLECTION]"
    echo "  -s STACK       Specify a stack to restart (WEBS, AGENT, SERVICE, AUTH, or ALL). If not specified, no restarts will occur."
    echo "  -c COLLECTION  Specify a test collection (default: revocation)"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

while getopts ":s:c:" opt; do
    case ${opt} in
        s )
            STACK=$OPTARG
            ;;
        c )
            COLLECTION=$OPTARG
            ;;
        \? )
            usage
            ;;
    esac
done

if [ -n "$STACK" ]; then
    DEPLOYMENTS="${!STACK}"
    if [ -z "$DEPLOYMENTS" ]; then
        echo "Error: Invalid stack specified"
        usage
    fi
fi

"$SCRIPT_DIR/ha.sh" "$DEPLOYMENTS" "$COLLECTION"
