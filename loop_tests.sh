#!/bin/bash
nr=1

# Use the provided loop count argument or set a default value of 100
if [ $# -eq 0 ]; then
    loop_count=100
else
    loop_count=$1

    # Check if the input is a valid positive integer
    re='^[0-9]+$'
    if ! [[ $loop_count =~ $re ]]; then
        echo "Error: Please enter a valid positive integer."
        exit 1
    fi
fi

# Loop based on the user input
while [[ $nr -le $loop_count ]]; do
    echo "This is run ${nr}"
    ./manage tests
    ./manage down
    ((nr=nr+1))
done
