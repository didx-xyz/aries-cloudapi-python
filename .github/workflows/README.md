# CI/CD

:warning: WIP

When deploying with `cloud_api_helm`, symlink `./shared_models` dir inside `helm/Chart/assets/shared_models`, e.g.:

```sh
git clone git@github.com:didx-xyz/cloud_api_helm.git helm/Chart
mkdir helm/Chart/assets
cd helm/Chart/assets
ln -s ../../../shared_models .
cd ../../../
```

From the root of this repo:

```sh
PROJECTS=(
  governance-ga-agent
  governance-ga-web
  governance-multitenant-agent
  governance-multitenant-web
  governance-trust-registry
  governance-webhooks-web
)

for PROJECT in "${PROJECTS[@]}"; do
  helm -n app upgrade --install --atomic --timeout=300s \
    $PROJECT \
    -f "./helm/Values/$PROJECT.yaml" \
    ./helm/Chart/.
done 
```