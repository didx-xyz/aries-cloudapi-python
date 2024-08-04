FROM python:3.13.0rc1-slim

COPY trustregistry /trustregistry
COPY shared /shared

WORKDIR /trustregistry

RUN pip install "poetry==1.8.3"
# Set Poetry's cache and virtualenvs path to a writable directory
ENV POETRY_CACHE_DIR=/tmp/.cache/pypoetry
RUN poetry config cache-dir $POETRY_CACHE_DIR && \
  poetry config virtualenvs.path $POETRY_CACHE_DIR/virtualenvs && \
  poetry install

EXPOSE 8001

USER nobody

CMD ["poetry", "run", "uvicorn", "trustregistry.main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
