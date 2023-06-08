FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY app /app/
COPY shared /shared

WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
