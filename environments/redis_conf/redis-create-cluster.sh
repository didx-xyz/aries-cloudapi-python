#!/bin/bash
sleep 10

node_1_ip=$(getent hosts redis-cluster-node-1 | awk '{ print $1 }')
node_2_ip=$(getent hosts redis-cluster-node-2 | awk '{ print $1 }')
node_3_ip=$(getent hosts redis-cluster-node-3 | awk '{ print $1 }')

redis-cli --cluster create $node_1_ip:6379 $node_2_ip:6379 $node_3_ip:6379 --cluster-replicas 1 --cluster-yes
