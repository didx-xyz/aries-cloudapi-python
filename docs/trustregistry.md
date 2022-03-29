### Trust registry

The [trust registry](http://localhost:8001/docs) is the gatekeeper interface for interactions in the sense that it keeps track of of truth states about actors, their respective roles as issuers and/or verifiers, and schemas.

The [Swagger docs](http://localhost:8001/docs) consist of three main sections:

- actor - for actor information and actions on the ledger
- schema - for schema information and actions on the ledger
- default - get all information from the registry

The trust registry provides access to this data via `actors` and `schemas` keys (of the JSON blob one retrieves from requesting the endpoint). They have the following structures:

```
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
      "didcomm_invitation": null
    },
    ...
}
```

where the fields should be self-explanatory (aka are lft as an exercise to the reader) and

```
{
    "schemas": [
        "z5Bug71M7Sj7cYpbVBDmN:2:test_schema:0.3",
        "MnspmfkzjLXd6WXyjCYJKW:2:test_schema:0.3",
        "E2HWvrZYs9SCXXHCZtFV1U:2:test_schema:0.3",
        ...
    ]
}
```

with `"z5Bug71M7Sj7cYpbVBDmN:2:test_schema:0.3"` representing schema ID, name and version respectively.

NOTE: In production, this should not be exposed to the www or interacted with directly. Either, refrain from exposing this to the www or setup a separate security layer for the trust registry. The simple reason for this being that you will want to disable arbitrary people from making changes to the trust registry.
