FROM python:3.12-slim

WORKDIR /tests

# Copy the pyproject.toml for each submodule
COPY app/pyproject.toml app/
COPY endorser/pyproject.toml endorser/
COPY trustregistry/pyproject.toml trustregistry/
COPY webhooks/pyproject.toml webhooks/

# Copy the lock files for each submodule
COPY app/poetry.lock app/
COPY endorser/poetry.lock endorser/
COPY trustregistry/poetry.lock trustregistry/
COPY webhooks/poetry.lock webhooks/

# Copy and run the install dependencies script
COPY scripts/install_all_dependencies.sh .
RUN bash install_all_dependencies.sh

COPY . .

# docker compose overwrites this
CMD ["pytest", "--junitxml=test_output.xml"]
