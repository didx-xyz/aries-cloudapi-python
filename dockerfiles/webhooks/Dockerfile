FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY webhooks /webhooks
COPY shared_models /shared_models

WORKDIR /webhooks

RUN pip install -r requirements.txt

EXPOSE 3010

CMD ["uvicorn", "webhooks.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
