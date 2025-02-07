# CI/CD

The CI/CD pipeline is defined in the [cicd.yml](cicd.yml) file.

```mermaid
---
title: CI/CD Pipeline
---
flowchart LR
    Format(Check code<br>formatting) ---> Build(Build/Push all<br>Docker Images)
    Unit(Run Unit Tests) ---> Build(Build/Push all<br>Docker Images)
    Build ---> Local(Deploy and Test local<br>ephemeral k8s)
    Build ---> Deploy(Deploy and Test EKS)
```

Refer to the [helm](../../helm) directory for the Helm charts and Helmfile
configs to deploy acapy-cloud.
