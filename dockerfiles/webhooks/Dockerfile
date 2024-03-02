FROM python:3.13.0a4-slim

COPY webhooks /webhooks
COPY shared /shared

WORKDIR /webhooks

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3010

USER nobody

CMD ["uvicorn", "webhooks.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
