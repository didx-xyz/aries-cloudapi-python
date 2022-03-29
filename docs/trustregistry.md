### Trust registry

The [trust registry](http://localhost:8001/docs) is the gatekeeper interface for interactions in the sense that it keeps track of of truth states about actors, their respective roles as issuers and/or verifiers, and schemas.

The [Swagger docs](http://localhost:8001/docs) consist of three main sections:

- actor - for actor information and actions on the ledger
- schema - for schema information and actions on the ledger
- default - get all information from the registry

NOTE: In production, this should not be exposed to the www or interacted with directly. Either, refrain from exposing this to the www or setup a separate security layer for the trust registry. The simple reason for this being that you will want to disable arbitrary people from making changes to the trust registry.
