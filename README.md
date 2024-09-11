# aries-cloudapi-python

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/ceca5ac566f74a3a8bfb3095074117ad)](https://www.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/ceca5ac566f74a3a8bfb3095074117ad)](https://www.codacy.com/gh/didx-xyz/aries-cloudapi-python/dashboard?utm_source=github.com&utm_medium=referral&utm_content=didx-xyz/aries-cloudapi-python&utm_campaign=Badge_Coverage)

:construction: This project is currently under development. Please do not use
this in production.

## Overview

This project essentially comprises a [FastAPI](https://fastapi.tiangolo.com/)
application built around the
[Hyperledger Aries stack](https://github.com/hyperledger/), primarily tailored
for [Yoma](https://yoma.world)-specific use cases.

The FastAPI app serves as a wrapper around common workflows, facilitating
real-life applications of the stack. It acts as a form of middleware or interface
for client applications (e.g., a mobile app) and the backend stack, using
[Aries CloudController](https://github.com/didx-xyz/aries-cloudcontroller-python)
and [ACA-Py](https://github.com/hyperledger/aries-cloudagent-python). The aim is
to streamline a client's workflow by providing convenient API endpoints for
common workflows, such as creating wallets, managing connections, credentials,
proofs, and workflows.

Multiple API calls to the AriesCloudAgent can often be condensed into a single
call via this API. For example, creating a wallet, which involves writing to the
ledger, awaiting the result, accepting a TAA, creating a DID, and finally
creating the wallet itself, can be done in a single call. Convenient, isn't it?

## How to Run It

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

While this project was primarily developed to meet the needs of
[Yoma](https://yoma.world), it is an open-source project that can be used for
other Hyperledger Aries projects as well. We welcome contributions from
everyone. Feel free to engage in discussions, create a PR against a ticket, or
open an issue yourself, following the GitHub guidelines.

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
mise run poetry:install:all
```

To start the containers and run the tests:

```bash
pytest .
```

Or only the unit tests:

```bash
pytest --ignore=app/tests/e2e
```

You can specify the log level of the pytest output by using the `--log-cli-level`
flag.

```bash
pytest . --log-cli-level=DEBUG
```

This will output all log messages with a log level of `DEBUG` or higher.

To run specific tests, you can specify the path to the test file and the test
method. For example:

```bash
pytest app/tests/e2e/test_verifier.py::test_accept_proof_request_oob_v1 --log-cli-level=1
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
