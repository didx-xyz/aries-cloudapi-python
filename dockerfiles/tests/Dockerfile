FROM python:3.9-slim

WORKDIR /tests

COPY requirements.dev.txt .
COPY requirements.txt .
COPY app/requirements.txt app/
COPY endorser/requirements.txt endorser/
COPY trustregistry/requirements.txt trustregistry/
COPY webhooks/requirements.txt webhooks/

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# docker compose overwrites this
CMD ["pytest", "--junitxml=test_output.xml"]
