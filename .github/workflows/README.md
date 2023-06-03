# CI/CD

:warning: WIP

When deploying with [Helm repository](https://github.com/didx-xyz/cloud_api_helm), symlink the `./shared` dir inside `./helm/Chart/assets/shared`:

```sh
git clone git@github.com:didx-xyz/cloud_api_helm.git helm/Chart
mkdir helm/Chart/assets
cd helm/Chart/assets
ln -s ../../../shared .
```

From the root of this repo:

```sh
PROJECTS=(
  ledger-nodes
  ledger-browser
  tails-server
  governance-ga-agent
  governance-trust-registry
  governance-multitenant-web
  governance-webhooks-web
  governance-multitenant-agent
  governance-endorser
)

for PROJECT in "${PROJECTS[@]}"; do
  helm -n app upgrade --install --atomic --timeout=300s \
    $PROJECT \
    -f "./helm/Values/$PROJECT.yaml" \
    ./helm/Chart/.
done
```
