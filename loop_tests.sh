#!/bin/bash
nr=1
while true; do
    echo "this is run ${nr}"
    ./manage tests
    ./manage down
    ((nr=$nr+1))
done
