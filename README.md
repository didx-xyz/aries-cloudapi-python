[![Codacy Badge](https://api.codacy.com/project/badge/Grade/66120846a7ba4bd9939d94a32e86bfef)](https://app.codacy.com/gh/didx-xyz/aries-cloudapi-python?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Grade_Settings)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=didx-xyz_aries-cloudapi-python&metric=bugs)](https://sonarcloud.io/dashboard?id=didx-xyz_aries-cloudapi-python)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=didx-xyz_aries-cloudapi-python&metric=coverage)](https://sonarcloud.io/dashboard?id=didx-xyz_aries-cloudapi-python)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=didx-xyz_aries-cloudapi-python&metric=sqale_rating)](https://sonarcloud.io/dashboard?id=didx-xyz_aries-cloudapi-python)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=didx-xyz_aries-cloudapi-python&metric=vulnerabilities)](https://sonarcloud.io/dashboard?id=didx-xyz_aries-cloudapi-python)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=didx-xyz_aries-cloudapi-python&metric=reliability_rating)](https://sonarcloud.io/dashboard?id=didx-xyz_aries-cloudapi-python)

# aries-cloudapi-python
## WIP
:warning: This is currently initial development work in progress. Please, do not use this in production.

## Overview
This project is a essentially comprises a [FastAPI](fastapi.tiangolo.com/) app around the [hyperledger aries stack](https://github.com/hyperledger/). Primarily tailored around [YOMA](yoma.africa)-specific usecases. The FastAPI app serves as a wrapper around common workflow for real-life applications of the stack. You can think of it as a wrapper, a form of middleware, or interface for client applications (for instance a mobile app) and the backend stack (using [Aries Cloudcontroller](https://github.com/didx-xyz/aries-cloudcontroller-python) under the hood and [Aca-py](https://github.com/hyperledger/aries-cloudagent-python) in the back - like a mullet). The aim is to facilitate a client's workflow by providing some convenience API endpoints for common workflows like creating wallets, managing wallets, their connections, and credentials, proofs and workflows. What is multiple API calls to the AriesCloudAgent can often be achieved with a single call via this API. For example, you want to create a wallet, which involves writing to the ledger, waiting for the result, getting and accepting a TAA, creating a DID and creating the wallet itself can be done in a single blow - how convenient, isn't it.

As this is under heavy deveopment still, we will soon provide more detailed instructions with examples, about how to use the API in a real-world scenario. There should also be hosting instructions following.

## How to run it
Running it is pretty straight forward - it's all containers. Simply run `./manage up` from the root of the project. This should spin up and provision all you need. You can visit [localhost:8000/api/doc](localhost:8000/api/doc) for the swagger docs and start palying about.

If you are familiar with Make you can also have a look in the Makefile to find some handy methods for running the project.

### Requirements (though)
There are some requirements for running the project, namely Docker and docker-compose as well as being able to run a POSIX shell (e.g. sh or bash).

In order to install Docker follow the instructions for your operating on their [official docs](https://docs.docker.com/engine/install/).

Proceed to follow the instructions for docker-compose corollary on [their docs](https://docs.docker.com/compose/install/).

If you experience any issues running the project, please, feel free to reach out by e.g. opening an issue or contacting one of the contributors.

## Contributing
Although this project is foremost developed to fit the needs of [YOMA](yoma.africa) it eventually is an open-source project that hopefully can get picked up and used for other aries-hyperledger projects as well. We do welcome contributions from anyone. Feel free to engage in discussions, create a PR against a ticket or open an issue yourself following the GitHub guidelines.
