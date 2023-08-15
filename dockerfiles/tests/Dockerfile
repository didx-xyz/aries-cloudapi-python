FROM python:3.9

WORKDIR /tests

COPY requirements.dev.txt .
COPY requirements.txt .
COPY app/requirements.txt app/
COPY endorser/requirements.txt endorser/
COPY trustregistry/requirements.txt trustregistry/
COPY webhooks/requirements.txt webhooks/

RUN pip install -r requirements.txt -r requirements.dev.txt

COPY . .

CMD ["pytest", "--junitxml=test_output.xml"]
