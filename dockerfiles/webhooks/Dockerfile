# Must be version 3.7 for now - bug in higher versions similar to https://github.com/tiangolo/fastapi/issues/2123
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7 

COPY webhooks /webhooks

WORKDIR /webhooks

RUN pip install -r requirements.txt

EXPOSE 3010

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
