FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY app /app
COPY shared /shared

WORKDIR /app

# If needing to download from test pypi
RUN cd /app && pip install -r requirements.txt


EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
