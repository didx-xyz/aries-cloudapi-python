FROM python:3.13.0b1-slim

COPY webhooks /webhooks
COPY shared /shared

WORKDIR /webhooks

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 3010

USER nobody

CMD ["uvicorn", "webhooks.web.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
