#!/usr/bin/env bash
# Prune all docker containers
docker system prune -a
# Prune all docker volumes
docker system prune --volumes
# List docker volumes
docker volume ls
# List docker containers
docker container ls -a
