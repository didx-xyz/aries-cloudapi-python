# https://fastapi.tiangolo.com/deployment/docker/?h=#when-to-use
# FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9
FROM python:3.9

COPY trustregistry /trustregistry
COPY shared /shared

WORKDIR /trustregistry

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8001

CMD ["uvicorn", "trustregistry.main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
