#!/bin/bash

i=0
echo waiting for containers to startup
# ./manage up-daemon-usecache
# sleep 60
while [ $i -le 240 ]
do
    STATUS1=$(curl -X 'GET' 'http://0.0.0.0:3021/status/live'  -H 'accept: application/json' | jq .alive)
    STATUS2=$(curl -X 'GET' 'http://0.0.0.0:4021/status/live'  -H 'accept: application/json' | jq .alive)
    sleep 1
    echo
    echo Waiting for container startup ${i}/240
    echo Agent 1 status: ${STATUS1}
    echo Agent 2 status: ${STATUS2}
    echo 
    if [[ $STATUS1 == 'true' && $STATUS2 == 'true'  ]]; then ((i=241)); fi  
    ((i++))
done
echo wait over