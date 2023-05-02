# aries-cloudapi-python

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/ceca5ac566f74a3a8bfb3095074117ad)](https://www.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/ceca5ac566f74a3a8bfb3095074117ad)](https://www.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Coverage)

## WIP

:warning: This is currently initial development work in progress. Please, do not use this in production.

## Overview

This project is a essentially comprises of a [FastAPI](fastapi.tiangolo.com/) app around the [hyperledger aries stack](https://github.com/hyperledger/) primarily tailored around [YOMA](yoma.africa)-specific use cases. The FastAPI app serves as a wrapper around common workflows for real-life applications of the stack. You can think of it as a wrapper, a form of middleware, or interface for client applications (for instance a mobile app) and the backend stack (using [Aries Cloudcontroller](https://github.com/didx-xyz/aries-cloudcontroller-python) under the hood and [Aca-py](https://github.com/hyperledger/aries-cloudagent-python) in the back - like a mullet). The aim is to facilitate a client's workflow by providing some convenience API endpoints for common workflows like creating wallets, managing wallets, their connections, and credentials, proofs and workflows. What is multiple API calls to the AriesCloudAgent can often be achieved with a single call via this API. For example, you want to create a wallet, which involves writing to the ledger, waiting for the result, getting and accepting a TAA, creating a DID and creating the wallet itself can be done in a single blow - how convenient, isn't it.

## How to run it

### Step 1: Run a local VON Network

Setup the VON network locally that will provide an instance of Hyperledger Indy ledger. Follow the instructions in the [VON Network README](https://github.com/bcgov/von-network/blob/main/README.md)

> NOTE: Ensure you start the VON Network with `--taa-sample` flag to enable TAA acceptance. For example:
>
> ```bash
> ./manage start --taa-sample
> ```
>
> This will start the VON Network with a sample TAA that you can use to accept the TAA. You can find the TAA in the `./von-network/config/sample_taa.json` and `./von-network/config/sample_aml.json` file.

### Step 2: Run the Aries Cloud Agent

> NOTE: Ensure the VON Network is running before starting the Cloud API. The Cloud API will try to connect to the VON Network and will fail if it is not running.

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

Install the requirements

```bash
pip install -r app/requirements.txt -r requirements.dev.txt -r trustregistry/requirements.txt
```

to start the containers and run the tests with

```bash
pytest .
```

or only the unit tests with:

```bash
pytest --ignore=app/tests/e2e
```

> NOTE:
> You can specify the log level of the pytest output by using the `--log-cli-level=DEBUG` flag. For example:
>
> ```bash
> pytest . --log-cli-level=DEBUG
> ```
>
> will output all log messages with a log level of `DEBUG` or higher.

To run specific tests you can specify the path to the test file or the test class or test method. For example:

```bash
pytest app/tests/e2e/test_verifier.py::test_accept_proof_request_oob_v1 --log-cli-level=0
```

## CI/CD

Please, refer to the [CI/CD docs](./.github/workflows/README.md) for more information.
