#!/bin/bash

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

usage() {
    echo "Usage: $0 [-s STACK] [-a]"
    echo "  -s STACK   Specify a single stack to test (WEBS, AGENT, SERVICE, AUTH, or ALL)"
    echo "  -a         Test all stacks sequentially"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

while getopts ":s:a" opt; do
    case ${opt} in
        s )
            STACK=$OPTARG
            ;;
        a )
            TEST_ALL=true
            ;;
        \? )
            usage
            ;;
    esac
done

if [ -n "$STACK" ] && [ "$TEST_ALL" = true ]; then
    echo "Error: Cannot specify both a single stack and all stacks"
    usage
fi

if [ -n "$STACK" ]; then
    $SCRIPT_DIR/ha_revocation.sh -s "$STACK"
elif [ "$TEST_ALL" = true ]; then
    for stack in WEBS AGENT SERVICE AUTH; do
        $SCRIPT_DIR/ha_revocation.sh -s "$stack"
    done
else
    usage
fi
