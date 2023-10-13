FROM python:3.9-slim

COPY app /app
COPY shared /shared

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

USER nobody

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
