#!/bin/bash

for r in $(grep 'image: \${ECR_REGISTRY}' docker-compose.yml | sed -e 's/^.*\///')
do
  aws ecr create-repository --repository-name "$r"
done
