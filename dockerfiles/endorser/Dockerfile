FROM python:3.12-slim

COPY endorser /endorser
COPY shared /shared

WORKDIR /endorser

RUN pip install --no-cache-dir -r requirements.txt --upgrade

EXPOSE 3009

USER nobody

CMD ["uvicorn", "endorser.main:app", "--reload", "--host", "0.0.0.0", "--port", "3009"]
