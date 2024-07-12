FROM python:3.12-slim

COPY webhooks /webhooks
COPY shared /shared

WORKDIR /webhooks

RUN pip install "poetry==1.8.3"
RUN poetry install

EXPOSE 3010

USER nobody

CMD ["uvicorn", "webhooks.web.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
