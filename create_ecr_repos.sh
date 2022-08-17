#!/bin/bash

#for r in $(grep 'container_name:' docker-compose.yaml | sed -e 's/^.*\///')
#do
#  #echo "test $r"
#  aws ecr create-repository --repository-name "$r"
#done

for r in $(grep 'image: \${ECR_REGISTRY}' docker-compose.yaml | sed -e 's/^.*\///')
do
  #echo "$r"
  aws ecr create-repository --repository-name "$r"
done