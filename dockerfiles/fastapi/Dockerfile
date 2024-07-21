FROM python:3.13.0b3-slim

COPY app /app
COPY shared /shared

WORKDIR /app

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 8000

USER nobody

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
