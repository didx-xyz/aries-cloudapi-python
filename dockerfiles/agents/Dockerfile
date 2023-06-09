FROM aries-cloudagent:py36-1.16-1_0.8.1

RUN pip3 install -U pip==21.3.1
# Install our 0.8.1 hotfix
RUN pip3 install aries-cloudagent@git+https://github.com/didx-xyz/aries-cloudagent-python.git@0.8.1-hotfix2

ADD configuration ./configuration
ADD scripts ./scripts