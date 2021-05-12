FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY ./app /app
# ADD app /app

WORKDIR /app

RUN pip install -r requirements.txt

# CMD ["uvicorn", "main:app", "--reload"]

# EXPOSE 8000