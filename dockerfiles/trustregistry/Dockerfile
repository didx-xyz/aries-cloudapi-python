FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

COPY trustregistry /trustregistry
COPY shared /shared

WORKDIR /trustregistry

RUN pip install -r requirements.txt

EXPOSE 8001

CMD ["uvicorn", "trustregistry.main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
