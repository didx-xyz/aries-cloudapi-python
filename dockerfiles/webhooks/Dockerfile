FROM python:3.13.0rc1-slim

COPY webhooks /webhooks
COPY shared /shared

WORKDIR /webhooks

RUN pip install "poetry==1.8.3"
# Set Poetry's cache and virtualenvs path to a writable directory
ENV POETRY_CACHE_DIR=/tmp/.cache/pypoetry
RUN poetry config cache-dir $POETRY_CACHE_DIR && \
  poetry config virtualenvs.path $POETRY_CACHE_DIR/virtualenvs && \
  poetry install

EXPOSE 3010

USER nobody

CMD ["poetry", "run", "uvicorn", "webhooks.web.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
