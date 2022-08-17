#!/bin/bash

#ECR_REGISTRY=""
#
## get parameters
#while getopts v: flag
#do
#  case "${flag}" in
#    v) ECR_REGISTRY=${OPTARG};;
#  esac
#done

for r in $(grep 'container_name:' docker-compose.yaml | sed -e 's/^.*\///')
do
  #echo "test $r"
  aws ecr create-repository --repository-name "$r"
done

#for r in $(grep 'image: \${ECR_REGISTRY}' docker-compose.yaml | sed -e 's/^.*\///')
#do
#  aws ecr create-repository --repository-name "$r"
#done
