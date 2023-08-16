#!/bin/bash
nr=1

# Use the provided loop count argument or set a default value of 100
if [ $# -eq 0 ]; then
    loop_count=100
    ./manage tests
    ./manage down
    ((nr=nr+1))
done
