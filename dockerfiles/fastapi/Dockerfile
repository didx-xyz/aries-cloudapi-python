FROM python:3.12-slim

COPY app /app
COPY shared /shared

WORKDIR /app

RUN pip install "poetry==1.8.3"
RUN poetry install

EXPOSE 8000

USER nobody

CMD ["poetry", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
