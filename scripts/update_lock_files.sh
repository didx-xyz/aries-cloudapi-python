#!/bin/bash

set -e

POETRY_VERSION="1.8.3"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check if Poetry is installed
if command_exists poetry; then
  echo "Poetry is already installed."
else
  echo "Poetry is not installed. Installing Poetry..."
  pip install "poetry==${POETRY_VERSION}"
  echo "Poetry installed successfully."
fi

# Array of submodules
submodules=("app" "endorser" "trustregistry" "webhooks")

# Generate lock files for each submodule
for submodule in "${submodules[@]}"; do
  echo "Generating lock file for $submodule..."
  cd $submodule
  poetry lock
  cd ..
done

echo "Lock files generated for all submodules."
