FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY trustregistry /app

WORKDIR /app

RUN cd /app && pip install -r requirements.txt

EXPOSE 8001

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8001"]
