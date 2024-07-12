FROM python:3.12-slim

WORKDIR /tests

COPY scripts/install_all_dependencies.sh .

RUN bash install_all_dependencies.sh

COPY . .

# docker compose overwrites this
CMD ["pytest", "--junitxml=test_output.xml"]
