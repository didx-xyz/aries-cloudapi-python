# K6 Load Testing Scripts

⚠️ Disclaimer: This is a work in progress. Refactoring and standardisation
pending... ⚠️

Initial load testing scripts and GH Actions pipeline config to run K6 in
parallel with K8s Pytests.

- Initial K6 flows:
  - setup function to create schema, issuer and cred def
  - create holders
  - establish connections
  - issue credentials
  - proof requests

## Running K6 Scripts

Configure local environment variables:

```sh
cp env.local .env.local
```

### Shipping local k6 metrics to Datadog

```
DOCKER_CONTENT_TRUST=1 \
docker run -d \
    --name datadog \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v /proc/:/host/proc/:ro \
    -v /sys/fs/cgroup/:/host/sys/fs/cgroup:ro \
    -e DD_SITE="datadoghq.eu" \
    -e DD_API_KEY=<YOUR_DATADOG_API_KEY> \
    -e DD_DOGSTATSD_NON_LOCAL_TRAFFIC=1 \
    -p 8125:8125/udp \
    datadog/agent:latest
```

## Running Biome to lint/format code

```sh
# Use mise to install Node
mise install

# Use npm to install Biome - `ci` for frozen lockfile
npm ci

# check formatting but don't actually write anything
npm run format:check

# format code
npm run format

# check linting but don't try to auto-fix
npm run lint

# lint and auto-fix if possible
npm run lint:fix
```
