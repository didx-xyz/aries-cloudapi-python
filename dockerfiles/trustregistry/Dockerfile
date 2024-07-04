FROM python:3.13.0b2-slim

COPY trustregistry /trustregistry
COPY shared /shared

WORKDIR /trustregistry

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 8001

USER nobody

CMD ["uvicorn", "trustregistry.main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
