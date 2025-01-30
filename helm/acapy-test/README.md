# Aca-Py Test Helm Chart

A Helm chart for deploying AcaPy Cloud containerized tests in a Kubernetes environment.

## Overview

This Helm chart deploys a test environment for AcaPy Cloud, facilitating automated testing through pytest.
It supports both standard test runs and regression testing scenarios.

## Prerequisites

- Kubernetes 1.18+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure (if persistence is enabled)

## Installing the Chart

To install the chart with the release name `my-release`:

```bash
helm install my-release .
```

## Configuration

The following table lists the configurable parameters of the chart and their default values.

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `nameOverride` | Override the name of the chart | `""` |
| `fullnameOverride` | Override the full name of the chart | `acapy-test` |
| `replicaCount` | Number of replicas to run | `1` |

### Image Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.registry` | Image registry | `ghcr.io/didx-xyz` |
| `image.name` | Image name | `d-cloud/pytest` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `Always` |
| `imagePullSecrets` | Image pull secrets | `[]` |

### Pod Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `podLabels` | Additional labels for pods | `{"sidecar.istio.io/inject": "false"}` |
| `podAnnotations` | Additional annotations for pods | `{}` |
| `podSecurityContext` | Pod security context | `{}` |
| `securityContext` | Container security context | `{}` |

### Service Account Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.automount` | Automount service account token | `false` |
| `serviceAccount.annotations` | Service account annotations | `{}` |
| `serviceAccount.name` | Service account name | `""` |

### Persistence Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistence | `false` |
| `persistence.mountPath` | Mount path for persistent volume | `/mnt` |
| `persistence.capacity` | Storage capacity | `1Gi` |
| `persistence.storageClassName` | Storage class name | `""` |

### Test Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `completions` | Number of test completions required | `1` |
| `command` | Test command to execute | See [values.yaml](conf/local/values.yaml) |

### Environment Variables

The chart supports two types of environment variables:

1. Regular environment variables (`env`)
2. Secret configuration (`secretConfig`)

Check the values.yaml file for the complete list of available environment variables.

## Regression Testing

The chart includes special configuration for regression testing through `regression.yaml`. Key features include:

- Support for running regression tests with `env.RUN_REGRESSION_TESTS=true`
- Fail when attempting to create fixtures (`env.FAIL_ON_RECREATING_FIXTURES`) that are expected to already exist
- JUnit XML report generation
- Coverage reporting

To run regression tests:

```bash
helm install my-release . -f regression.yaml
```

## Resource Management

Resource requests and limits can be configured using the `resources` parameter:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 100m
    memory: 128Mi
```

## Scheduling

The chart supports node selection and pod scheduling through:

- `nodeSelector`: Node labels for pod assignment
- `tolerations`: Pod tolerations
- `affinity`: Pod affinity rules

## Notes

- The chart generates test output and coverage reports in the `/mnt` directory when persistence is enabled
- Default configuration assumes the presence of various services (governance-agent, tails-server, etc.)
- API keys and JWT secrets should be properly configured in production environments
