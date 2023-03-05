[![Codacy Badge](https://app.codacy.com/project/badge/Grade/ceca5ac566f74a3a8bfb3095074117ad)](https://www.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/ceca5ac566f74a3a8bfb3095074117ad)](https://www.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Coverage)

# aries-cloudapi-python

## WIP

:warning: This is currently initial development work in progress. Please, do not use this in production.

## Overview

This project is a essentially comprises of a [FastAPI](fastapi.tiangolo.com/) app around the [hyperledger aries stack](https://github.com/hyperledger/) primarily tailored around [YOMA](yoma.africa)-specific use cases. The FastAPI app serves as a wrapper around common workflows for real-life applications of the stack. You can think of it as a wrapper, a form of middleware, or interface for client applications (for instance a mobile app) and the backend stack (using [Aries Cloudcontroller](https://github.com/didx-xyz/aries-cloudcontroller-python) under the hood and [Aca-py](https://github.com/hyperledger/aries-cloudagent-python) in the back - like a mullet). The aim is to facilitate a client's workflow by providing some convenience API endpoints for common workflows like creating wallets, managing wallets, their connections, and credentials, proofs and workflows. What is multiple API calls to the AriesCloudAgent can often be achieved with a single call via this API. For example, you want to create a wallet, which involves writing to the ledger, waiting for the result, getting and accepting a TAA, creating a DID and creating the wallet itself can be done in a single blow - how convenient, isn't it.

## How to run it

Export the necessary environment variables

```sh
export ECR_REGISTRY=324190738845.dkr.ecr.af-south-1.amazonaws.com
# ECR_REGISTRY doesn't need to be valid for `./manage up` or `make start`
# It is only used when building and pushing via docker-compose
```

Running it is pretty straight forward - it's all containers. Simply run `./manage up` or `make start` from the root of the project. This should spin up and provision all you need. You can visit [localhost:8000/api/doc](localhost:8000/api/doc) for the swagger docs and start playing about.

If you are familiar with Make you can also have a look in the Makefile to find some handy methods for running the project.

### Requirements

There are some requirements for running the project, namely Docker and docker-compose as well as being able to run a POSIX shell (e.g. sh or bash).

In order to install Docker follow the instructions for your operating on their [official docs](https://docs.docker.com/engine/install/).

Proceed to follow the instructions for docker-compose corollary on [their docs](https://docs.docker.com/compose/install/).

If you experience any issues running the project, please, feel free to reach out by e.g. opening an issue or contacting one of the contributors.

## Docs

You can find more detailed documentation in the [`./docs` folder](https://github.com/didx-xyz/aries-cloudapi-python/tree/development/docs). Most useful will be the `intro` and `workflow` sections.

## Contributing

Although this project is foremost developed to fit the needs of [YOMA](yoma.africa) it eventually is an open-source project that hopefully can get picked up and used for other aries-hyperledger projects as well. We do welcome contributions from anyone. Feel free to engage in discussions, create a PR against a ticket or open an issue yourself following the GitHub guidelines.

## Running tests

The tests use `pytest`. For convenience use GNU Make to run them. First ensure the project is running locally by running `make start`. In another shell you can now run `make tests` to run all tests or `make unit-tests` to run only the unit tests.

Without using `make` you can run:

```bash
./manage up
```

to start the containers and run the tests with

```bash
pytest .
```

or only the unit tests with:

```bash
pytest --ignore=app/tests/e2e
```

## CI/CD

:warning: WIP

When deploying with `cloud_api_helm`, symlink `./shared_models` dir inside `helm/Chart/assets/shared_models`, e.g.:

```sh
git clone git@github.com:didx-xyz/cloud_api_helm.git helm/Chart
mkdir helm/Chart/assets
cd helm/Chart/assets
ln -s ../../../shared_models .
cd ../../../
```

From the root of this repo:

```sh
PROJECTS=(
  governance-ga-agent
  governance-ga-web
  governance-multitenant-agent
  governance-multitenant-web
  governance-trust-registry
  governance-webhooks-web
)

for PROJECT in "${PROJECTS[@]}"; do
  helm -n app upgrade --install --atomic --timeout=300s \
    $PROJECT \
    -f "./helm/Values/$PROJECT.yaml" \
    ./helm/Chart/.
done 
```
