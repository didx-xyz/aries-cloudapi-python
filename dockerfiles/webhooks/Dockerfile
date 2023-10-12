## https://fastapi.tiangolo.com/deployment/docker/?h=#when-to-use
# FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9
FROM python:3.9

COPY webhooks /webhooks
COPY shared /shared

WORKDIR /webhooks

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 3010

CMD ["uvicorn", "webhooks.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
