FROM python:3.12-slim

COPY endorser /endorser
COPY shared /shared

WORKDIR /endorser

RUN apt-get -y update
RUN apt-get -y install git

RUN pip install --no-cache-dir -r requirements.txt -r requirements.dev.txt --upgrade

EXPOSE 3009

USER nobody

CMD ["uvicorn", "endorser.main:app", "--reload", "--host", "0.0.0.0", "--port", "3009"]
