FROM python:3.12-slim

WORKDIR /cloudapi-tests

# Copy source code for each module
COPY app app
COPY endorser endorser
COPY trustregistry trustregistry
COPY waypoint waypoint
COPY shared shared

# Install all dependencies
ARG POETRY_VERSION=2.0.1
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

ENV POETRY_VIRTUALENVS_CREATE=false
ARG MODULES="app endorser trustregistry waypoint"
RUN for module in ${MODULES}; do \
  cd "/cloudapi-tests/$module" && poetry install; \
  done

USER nobody

# docker compose overwrites this
CMD ["pytest", "--junitxml=test_output.xml"]
