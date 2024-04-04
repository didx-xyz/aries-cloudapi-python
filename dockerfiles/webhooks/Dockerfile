FROM python:3.12-slim

COPY webhooks /webhooks
COPY shared /shared

WORKDIR /webhooks

RUN apt-get -y update
RUN apt-get -y install git

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 3010

USER nobody

CMD ["uvicorn", "webhooks.web.main:app", "--reload", "--host", "0.0.0.0", "--port", "3010"]
