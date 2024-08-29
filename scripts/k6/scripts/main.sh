#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source "$SCRIPT_DIR/config.sh"
source "$SCRIPT_DIR/collections.sh"

usage() {
    echo "Usage: $0 [-s STACK] [-c COLLECTION]"
    echo "  -s STACK       Specify a stack to test (WEBS, AGENT, SERVICE, AUTH, or ALL)"
    echo "  -c COLLECTION  Specify a test collection (default: revocation)"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

COLLECTION="revocation"
STACK=""

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

if [ -z "$STACK" ]; then
    usage
fi

DEPLOYMENTS="${!STACK}"

if [ -z "$DEPLOYMENTS" ]; then
    echo "Error: Invalid stack specified"
    usage
fi

"$SCRIPT_DIR/ha_revocation.sh" "$DEPLOYMENTS" "$COLLECTION"
