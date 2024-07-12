FROM python:3.12-slim

COPY endorser /endorser
COPY shared /shared

WORKDIR /endorser

RUN pip install "poetry==1.8.3"
RUN poetry install

EXPOSE 3009

USER nobody

CMD ["uvicorn", "endorser.main:app", "--reload", "--host", "0.0.0.0", "--port", "3009"]
