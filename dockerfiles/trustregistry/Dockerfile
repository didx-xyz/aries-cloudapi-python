FROM python:3.12.0b1-slim

COPY trustregistry /trustregistry
COPY shared /shared

WORKDIR /trustregistry

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8001

USER nobody

CMD ["uvicorn", "trustregistry.main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
