FROM python:3.12-slim

COPY trustregistry /trustregistry
COPY shared /shared

WORKDIR /trustregistry

RUN pip install "poetry==1.8.3"
RUN poetry install

EXPOSE 8001

USER nobody

CMD ["uvicorn", "trustregistry.main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
