# Trust Registry

As a client, you can retrieve the trust registry but not alter it. This design is intentional as only administrative
actions should modify the trust registry, and such actions are only possible with an admin role.

> NOTE: The Trust Registry GET API endpoint is not protected and should not be publicly accessible.

The [Trust Registry](http://trust-registry.cloudapi.127.0.0.1.nip.io/docs) serves
as a gatekeeper interface for interactions, maintaining the truth states about
actors, their respective roles as issuers and/or verifiers, and schemas.

The [Swagger docs](http://trust-registry.cloudapi.127.0.0.1.nip.io/docs) are
divided into three main sections:

- Actor - For actor information and actions on the ledger
- Schema - For schema information and actions on the ledger
- Default - To retrieve all information from the registry

The trust registry provides access to this data via `actors` and `schemas` keys, which can be found in the JSON blob
retrieved from requesting the endpoint. Their structures are as follows:

```json
{
    "actors": [
    {
      "name": "Test Actor-0.26703024264670694",
      "roles": [
        "issuer",
        "verifier"
      ],
      "did": "did:sov:XfbLjZFxgoznN24LUVxaQH",
      "id": "test-actor-0.26703024264670694",
      "didcomm_invitation": null,
      "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
    },
    ...
}
```

The fields here should be self-explanatory.

And,

```json
{
    "schemas": [
        "z5Bug71M7Sj7cYpbVBDmN:2:test_schema:0.3",
        "MnspmfkzjLXd6WXyjCYJKW:2:test_schema:0.3",
        "E2HWvrZYs9SCXXHCZtFV1U:2:test_schema:0.3",
        ...
    ]
}
```

where `"z5Bug71M7Sj7cYpbVBDmN:2:test_schema:0.3"` represents the schema ID, name, and version respectively.

> **_NOTE_**: In a production environment, this should not be exposed to the internet or interacted with directly.
> It's advisable to either avoid exposing this to the internet or set up a separate security layer for the trust
> registry. This is because it's crucial to prevent unauthorized individuals from making changes to the trust registry.

## Trust-registry Role in the application flows

Below we indicate where and how the Trust-registry is consulted to verify that Issuers/Verifiers and schemas are on the
Trust-registry.

### Create Credential Definition

```mermaid
---
title: Trust-registry called during credential definition creation
---
flowchart LR
    App(Create Credential Definition Request) -->|Consults| TR[Trust Registry]
    subgraph Trust Registry Checks
      TR -->|Validates| Check1{Issuer Authorization}
      Check1 -->|If Unauthorized| Block[⨯ Block Operation]
      Check1 -->|If Authorized| Check2{Schema exists on TR}
      Check2 -->|Not on TR| Block
    end
    Check2 -->|If Registered| Continue[✓ Proceed with Creation]
    
    style TR fill:#a8d1ff,stroke:#1e88e5,color:black
    style Block fill:#ffcdd2,stroke:#e53935,color:black
    style Continue fill:#c8e6c9,stroke:#43a047,color:black
```

---

### Credential issuance

```mermaid
---
title: Create Credential-Offer/Sending Credential
---
flowchart LR
    subgraph Request Types
        App1(Create Offer Request <br> Connectionless) --> Consults[Consults]
        App2(Send Credential Request<br>with Connection ID) --> Consults[Consults]
    end
    subgraph Trust Registry Checks
      Consults --> TR
      TR[Trust Registry] -- Validates --> Check1{Issuer<br>Authorization}
      Check1 -->|If Unauthorized| Block[⨯ Block Operation]
      Check1 -->|If Authorized| Check2{Schema<br>Registration}
      Check2 -->|Not on TR| Block
    end
    Check2 -->|If Registered| Proceed[Continue]
    

    subgraph Request Continue
      Proceed -->|Connectionless| Continue1[✓ Create Offer]
      Proceed -->|With Connection ID| Continue2[✓ Send Credential]
    end

    linkStyle 0,8 stroke:#ff7043,color:#ff7043, stroke-width:2
    linkStyle 1,9 stroke:#7cb342,color:#7cb342,stroke-width:2
    
    style TR fill:#a8d1ff,stroke:#1e88e5,color:black
    style Block fill:#ffcdd2,stroke:#e53935,color:black
    style Continue1 fill:#c8e6c9,stroke:#43a047,color:black
    style Continue2 fill:#c8e6c9,stroke:#43a047,color:black
    style Proceed fill:#c8e6c9,stroke:#43a047,color:black

```

---

```mermaid
---
title: Holder Request Credential
---
flowchart LR
  Start(Holder receives <br> Credential-Offer) --> Request[Request Credential]
  Request -->|Consults| TR[Trust Registry]
  subgraph Trust Registry Checks
    TR -->|Validates| Check1{Issuer Authorization}
    Check1 -->|If Unauthorized| Block[⨯ Block Operation]
    Check1 -->|If Authorized| Check2{Schema exists on TR}
    Check2 -->|Not on TR| Block
  end
  Check2 -->|If Registered| Continue[✓ Proceed with Credential Exchange]

  style TR fill:#a8d1ff,stroke:#1e88e5,color:black
  style Block fill:#ffcdd2,stroke:#e53935,color:black
  style Continue fill:#c8e6c9,stroke:#43a047,color:black
```

---

### Proof Requests

```mermaid
---
title: Verifier sends Proof Request
---
flowchart LR
  Start(Send Proof request) -->|Consult| TR[Trust-Registry]
  subgraph Trust Registry Checks
    TR -->|Validates| Check1{Verifier Authorization}
    Check1 -->|If Unauthorized| Block[⨯ Block Operation]
    Check1 -->|If Authorized| Check2{Schema exists on TR}
    Check2 -->|Not on TR| Block
  end
  Check2 -->|If Registered| Continue[✓ Proceed with <br> Sending Proof]
   
  style TR fill:#a8d1ff,stroke:#1e88e5,color:black
  style Block fill:#ffcdd2,stroke:#e53935,color:black
  style Continue fill:#c8e6c9,stroke:#43a047,color:black
```

---

```mermaid
---
title: Holder Receives Proof Request
---
flowchart LR
  Start(Accept Proof Request) -->|Consult| TR[Trust-Registry]
  subgraph Trust Registry Checks
    TR -->|Validates| Check1{Verifier Authorization}
    Check1 -->|If Unauthorized| Block[⨯ Block Operation]
    Check1 -->|If Authorized| Check2{Schema exists on TR}
    Check2 -->|Not on TR| Block
  end
  Check2 -->|If Registered| Continue[✓ Proceed with <br> Accepting Proof]
   
  style TR fill:#a8d1ff,stroke:#1e88e5,color:black
  style Block fill:#ffcdd2,stroke:#e53935,color:black
  style Continue fill:#c8e6c9,stroke:#43a047,color:black
```

---
