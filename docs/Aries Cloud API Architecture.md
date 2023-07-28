# Overview of Aries Cloud API Architecture

This document provides a brief overview of the Aries Cloud API Architecture, focusing on the two key components: the Admin Agent and the Multi-tenant Agent.

## Admin Agent

The Admin Agent and the Multi-tenant Agent are both exposed via the same Swagger UI under the same URL. They are differentiated based on the authorization method, which also specifies a role. For more information on this, refer to the workflows document.

The Admin Agent represents GOVERNANCE, or in a broader sense, the administrative entity. This non-multitenant agent is used for various administrative functions such as creating schemas, managing actors against the trust registry, and managing wallets.

## Multi-tenant Agent

Like the Admin Agent, the Multi-tenant Agent is also exposed via the same Swagger UI under the same URL, with distinction made based on the authorization method and role.

The Multi-tenant Agent is designed for sub-wallet and tenant management from the tenant's perspective.

For a more comprehensive understanding of multi-tenancy, please refer to the [ACA-Py docs](https://github.com/hyperledger/aries-cloudagent-python/blob/main/Multitenancy.md).
