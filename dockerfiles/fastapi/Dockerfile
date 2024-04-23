FROM python:3.12-slim

COPY app /app
COPY shared /shared

WORKDIR /app

RUN apt-get -y update
RUN apt-get -y install git

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 8000

USER nobody

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
