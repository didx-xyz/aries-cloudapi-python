FROM python:3.9-slim

WORKDIR /tests

# Copy requirements and install dependencies
COPY requirements.dev.txt .
COPY requirements.txt .
COPY app/requirements.txt app/
COPY endorser/requirements.txt endorser/
COPY trustregistry/requirements.txt trustregistry/
COPY webhooks/requirements.txt webhooks/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application
COPY . .

# Copy and set the custom script as the entry point
COPY ../scripts/run_tests.sh /tests/run_tests.sh
RUN chmod +x /tests/run_tests.sh
ENTRYPOINT ["/tests/run_tests.sh"]
