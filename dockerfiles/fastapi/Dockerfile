# https://fastapi.tiangolo.com/deployment/docker/?h=#when-to-use
# FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9
FROM python:3.9

COPY app /app
COPY shared /shared

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
