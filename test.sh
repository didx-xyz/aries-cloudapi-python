#!/bin/bash

i=0
echo waiting for dockers to startup
./manage up-daemon-usecache
while [ $i -le 240 ]
do
    STATUS1=$(curl -X 'GET' 'http://localhost:3021/status/live'  -H 'accept: application/json' 2>/dev/null | jq .alive)
    STATUS2=$(curl -X 'GET' 'http://localhost:4021/status/live'  -H 'accept: application/json' 2>/dev/null | jq .alive)
    if [[ $STATUS1 == 'true' && $STATUS2 == 'true'  ]]; then ((i=241)); fi  
    sleep 1
    echo waiting for container startup ${i}/240 ${STATUS1} ${STATUS2}
    ((i++))
done
echo wait over