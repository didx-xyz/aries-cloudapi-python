FROM python:3.8

COPY endorser /endorser

WORKDIR /endorser

RUN pip install -r requirements.txt -r requirements.dev.txt

WORKDIR /

CMD ["watchfiles", "python -m endorser.main", "/endorser"]
