FROM ghcr.io/hyperledger/aries-cloudagent-python:py3.9-indy-1.16.0-0.8.2

RUN pip3 install -U pip==21.3.1
RUN pip3 install aries-cloudagent==0.8.2

ADD configuration ./configuration
ADD scripts ./scripts