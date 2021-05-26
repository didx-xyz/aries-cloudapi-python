FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY app /app

WORKDIR /app

RUN cd /app && pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
