FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY trustregistry /trustregistry

WORKDIR /trustregistry

RUN cd /trustregistry && pip install -r requirements.txt

EXPOSE 8001

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
