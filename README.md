# didx-cloud

![Python](https://img.shields.io/badge/python-3.12-blue.svg)
[![Toolset: Mise](https://img.shields.io/badge/toolset-Mise-orange.svg?style=flat)](https://mise.jdx.dev/)
[![Dev Experience: Tilt](https://img.shields.io/badge/devex-Tilt-blue.svg?style=flat)](https://tilt.dev)
[![Codacy Badge](https://app.codacy.com/project/badge/Grade/ceca5ac566f74a3a8bfb3095074117ad)](https://app.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/ceca5ac566f74a3a8bfb3095074117ad)](https://app.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_coverage)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![DIDx GitHub](https://img.shields.io/badge/GitHub-DIDx-181717.svg?style=flat&logo=github)](https://github.com/didx-xyz)

:construction: This project is currently under development. If you would like to use
this in production, please contact us first to discuss your use case.

## Overview

This project comprises a [FastAPI](https://fastapi.tiangolo.com/) application built
around [ACA-Py](https://github.com/openwallet-foundation/aries-cloudagent-python),
primarily tailored for [Yoma](https://yoma.world)-specific use cases.

The FastAPI app serves as a wrapper around common workflows, facilitating
real-life applications of self-sovereign identity. It acts as an interface
for client applications (e.g., a mobile app) and the backend, using our
[OpenAPI client](https://github.com/didx-xyz/aries-cloudcontroller-python) and ACA-Py.

Multiple API calls to ACA-Py can be condensed into a single call through this API.
For instance, onboarding an issuer — which involves creating a wallet, establishing a
connection with an endorser, generating a public DID, accepting the Transaction Author
Agreement (TAA), publishing the DID to the ledger, and awaiting confirmation — can all
be achieved with a single API call. Convenient, isn't it?

We enable and simplify several key capabilities, including:

- Creating and managing wallets
- Onboarding issuers and verifiers
- Managing connections between parties
- Creating schemas and credential definitions
- Issuing verifiable credentials and handling revocations
- Requesting and validating proofs

## How to Run It

> [!NOTE]
> For local development we migrated away from Docker Compose and now use Tilt
> and Kind.
>
> The original `./manage` script and Docker Compose files are still available in
> this repository, however they are now deprecated, no longer maintained, and
> will be removed in the future.

Running the project is straightforward — it's all containerized. Simply execute
`mise run tilt:up` from the project root. This command will spin up a Kind
cluster, build all the necessary docker images, and start the project.
You can then visit [localhost:10350](http://localhost:10350) to access the Tilt
UI.

### Requirements

To run the project, you will need Docker and docker-compose, as well as the
ability to run a POSIX shell (e.g., sh or bash).

To install Docker, follow the instructions for your operating system in the
[official docs](https://docs.docker.com/engine/install/).

Next, follow the instructions for docker-compose in
[their docs](https://docs.docker.com/compose/install/).

If you experience any issues while running the project, feel free to reach out
by opening an issue or contacting one of the contributors.

### Setting up Mise

This project makes use of [Mise](https://mise.jdx.dev) to install and manage
dev tooling.

There are several options for installing Mise:

```sh
# Homebrew
brew install mise

# Build from source (if you have Rust installed)
cargo install mise

# Arch Linux User Repository
yay -S mise-bin

# Debian/Ubuntu APT (amd64)
sudo apt-get update -y && sudo apt-get install -y gpg wget curl
sudo install -dm 755 /etc/apt/keyrings
wget -qO - https://mise.jdx.dev/gpg-key.pub \
  | gpg --dearmor \
  | sudo tee /etc/apt/keyrings/mise-archive-keyring.gpg 1> /dev/null
echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.gpg arch=amd64] https://mise.jdx.dev/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/mise.list
sudo apt-get update
sudo apt-get install -y mise

# Debian/Ubuntu APT (arm64)
sudo apt-get update -y && sudo apt-get install -y gpg wget curl
sudo install -dm 755 /etc/apt/keyrings
wget -qO - https://mise.jdx.dev/gpg-key.pub \
  | gpg --dearmor \
  | sudo tee /etc/apt/keyrings/mise-archive-keyring.gpg 1> /dev/null
echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.gpg arch=arm64] https://mise.jdx.dev/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/mise.list
sudo apt-get update
sudo apt-get install -y mise
```

We _strongly_ recommend using your system package manager to install Mise.

Additional installation documentation can be found
[here](https://mise.jdx.dev/getting-started.html#alternate-installation-methods)

Once you have Mise installed, you will need to activate it in your shell.

```sh
# Bash
echo 'eval "$(mise activate bash)"' >> ~/.bashrc && source ~/.bashrc

# Zsh
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc && source ~/.zshrc

# Fish
echo 'mise activate fish | source' >> ~/.config/fish/config.fish && source ~/.config/fish/config.fish
```

Once Mise is installed and activated, you can run `mise trust` and then
`mise install` to install all the required tools.

Other shells are supported as well. Please refer to the
[Mise documentation](https://mise.jdx.dev/getting-started.html#shells) for more
information.

> [!NOTE]
> At the time of writing, Mise
> [does not support Windows](https://mise.jdx.dev/faq.html#windows-support).
> WSL is recommended for Windows users.
>
> If you are using WSL, you will need to take some
> [additional steps](https://kind.sigs.k8s.io/docs/user/using-wsl2/) for Kind to
> work.

## Docs

You can find more detailed documentation in the
[`./docs` folder](docs/README.md). The `Quick Start`, `Common Steps` and
`Example Flows` will be most useful.

## Contributing

[![Contributions](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](./CONTRIBUTING.md)

While this project was primarily developed to meet the needs of
[Yoma](https://yoma.world), it is an open-source project that can be used for
other Hyperledger Aries projects as well. We welcome contributions from
everyone. Feel free to engage in discussions, create pull requests against
existing tickets, or open new issues following the GitHub guidelines.

## Running Tests

The tests use `pytest`. For convenience, use Mise to run them. First, ensure
the project is running locally by executing `mise run tilt:up`. In another shell,
you can now run `mise run tests` to run all tests or `mise run tests:unit` to run
only the unit tests.

```bash
mise run tilt:up
```

Install the requirements:

```bash
mise run poetry:install
```

To run the tests you need to set up some environment variables to point Pytest
at the correct endpoints.

```bash
cp .env.example .env
source .env
```

Then you can run the tests:

```bash
poetry run pytest .
```

Or only the unit tests:

```bash
poetry run pytest --ignore=app/tests/e2e
```

You can specify the log level of the pytest output by using the `--log-cli-level`
flag.

```bash
poetry run pytest . --log-cli-level=DEBUG
```

This will output all log messages with a log level of `DEBUG` or higher.

To run specific tests, you can specify the path to the test file and the test
method. For example:

```bash
poetry run pytest \
  app/tests/e2e/test_verifier_oob.py::test_accept_proof_request_oob \
  --log-cli-level=1
```

## Running containerised tests

```bash
mise run tilt:up
```

In another terminal:

```bash
helmfile apply \
  --environment local \
  -f ./tilt/.charts/helmfiles/aries-capi-test.yaml
```

## CI/CD

Please, refer to the [CI/CD docs](./.github/workflows/README.md) for more
information.
