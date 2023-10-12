FROM ghcr.io/hyperledger/aries-cloudagent-python:py3.9-0.9.0

RUN pip3 install --no-cache-dir -U pip==21.3.1
RUN pip3 install --no-cache-dir aries-cloudagent==0.9.0

ADD configuration ./configuration
ADD scripts ./scripts
