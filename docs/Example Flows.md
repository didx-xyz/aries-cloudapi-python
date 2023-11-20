# Example Flow

This document will guide you through an end to end flow:

1. Onboarding an `Issuer`, `Verifier` and a `Holder`.
2. Creating a `Credential Schema`.
3. The `Issuer` creating a `Credential defenition`.
4. Issuing a credential to a `Holder`.
5. The `Verifier` doing a `proof request` against the `Holder's Credential`.
6. Server Sent Events (SSE) 

 >Please be aware that it is assumed at this point that your ecosystem has been [bootstraped](./Bootstrap%20Trust%20Ecosystem.md) with an endorser.
