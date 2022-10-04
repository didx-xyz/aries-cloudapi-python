# Aries Cloud API Architecture Overview
> TODO: Link to Yoma Architecture Documents

### Admin Agent

Both aca-py agents are exposed via the same Swagger UI under the same url. They are distinguished under the hood via the authorization method which also specifies a role. Please, refer to the workflows doc for further information.

The admin agent is a non-multitenant agent for general admin representing GOVERNANCE or in a broader sense of speaking the admin entity. This agent can be used to create schemas, manage actors (against the trust registry), and managing wallets.


### Multi-tenant agent

Both aca-py agents are exposed via the same Swagger UI under the same url. They are distinguished under the hood via the authorization method which also specifies a role. Please, refer to the workflows doc for further information.

This agent is meant for sub-wallet and tenant management from a tenant perspective.

For more information on multi-tenancy please refer to the [aca-py docs](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Multitenancy.md).
