FROM python:3.9

COPY endorser /endorser
COPY shared /shared

WORKDIR /endorser

RUN pip install --no-cache-dir -r requirements.txt -r requirements.dev.txt

WORKDIR /

CMD ["watchfiles", "python -m endorser.main", "/endorser"]
