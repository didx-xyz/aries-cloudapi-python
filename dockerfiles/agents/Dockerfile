ARG BBS_SUFFIX="-bbs"
FROM ghcr.io/didx-xyz/acapy-agent${BBS_SUFFIX}:py3.12-release-1.2.1-20250130

USER root

# Install Google Protobuf
ARG PROTOBUF_VERSION=5.29.3
RUN pip install --no-cache-dir protobuf==${PROTOBUF_VERSION} \
  git+https://github.com/didx-xyz/acapy-wallet-groups-plugin@396eeb4290 \
  git+https://github.com/didx-xyz/acapy-plugins@b3c593f103aa#subdirectory=nats_events

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
