FROM python:3.12-slim

COPY app /app
COPY shared /shared

WORKDIR /app

RUN pip install "poetry==1.8.3"
# Set Poetry's cache and virtualenvs path to a writable directory
ENV POETRY_CACHE_DIR=/tmp/.cache/pypoetry
RUN poetry config cache-dir $POETRY_CACHE_DIR && \
  poetry config virtualenvs.path $POETRY_CACHE_DIR/virtualenvs && \
  poetry install

EXPOSE 8000

USER nobody

CMD ["poetry", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
