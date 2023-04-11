#!/bin/bash

for r in $(grep 'container_name: ' docker-compose.yaml | sed -e 's/^.*container_name\://')
do
  #echo "$r"
  aws ecr create-repository --repository-name "$r"
done

#echo "XXXXX"
#for r in $(grep 'image: \${ECR_REGISTRY}' docker-compose.yaml | sed -e 's/^.*\///' | sed 's/:.*//')
#do
#  #echo "$r"
#  aws ecr create-repository --repository-name "$r"
#done