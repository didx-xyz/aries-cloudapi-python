ARG BBS_SUFFIX="-bbs"
FROM ghcr.io/didx-xyz/acapy-agent${BBS_SUFFIX}:py3.12-1.2.0-20250127

USER root

# Install Google Protobuf
ARG PROTOBUF_VERSION=5.29.3
RUN pip install --no-cache-dir protobuf==${PROTOBUF_VERSION} \
  acapy-wallet-groups-plugin==1.2.0.post20250127 \
  git+https://github.com/didx-xyz/aries-acapy-plugins@1.2.0-20250127#subdirectory=nats_events

COPY scripts/startup.sh startup.sh
RUN chmod +x ./startup.sh

USER aries

ENTRYPOINT [ "./startup.sh" ]
## Governance Agent
CMD [ "--wallet-type", "askar", \
  "--plugin", "nats_events.v1_0.nats_queue.events", \
  ## Multitenant Agent
  #   "--auto-promote-author-did", \
  #   "--plugin", "acapy_wallet_groups_plugin", \
  "--plugin-config-value", "nats_queue.connection.connection_url=\"nats://nats-1:4222\""]
