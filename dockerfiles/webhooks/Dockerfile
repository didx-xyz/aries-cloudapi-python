FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY webhooks /webhooks

WORKDIR /webhooks

RUN pip install -r requirements.txt

EXPOSE 3010

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
