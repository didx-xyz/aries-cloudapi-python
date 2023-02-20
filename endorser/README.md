# Endorser

The endorser service listens for endorser events from the governance agent and will endorse any requests that match the rules defined in the trust registry.

## Rules

The following endorsement types are implemented in the endorser service. More can be added by adding processors and handlers in the `endorser_processor.py` file.

### Credential Definition Endorsement for Issuers

Currently the ecosystem is built around the notion that only tenants registered with the role of issuer in the trust registry can create credential definitions. They are only allowed to create credential definitions for schemas that are also registered in the trust registry.

The following checks are done before accepting the endorsement request:

- Request is for credential definition
- Did of transaction author is registered with role `issuer` in the trust registry
- Schema used in the credential definition is registered in the trust registry.
