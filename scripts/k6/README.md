### K6 Load Testing Scripts
⚠️ Discalimer: This is a work in progress. Refactoring and standardisation pending... ⚠️

Initial load testing scripts and GH Actions pipeline config to run K6 in parallel with K8s Pytests.

- Initial K6 flows:
  - setup function to create schema, issuer and cred def
  - create holders
  - establish connections
  - issue credentials
  - proof requests


### Running K6 Scripts
Configure local environment variables:
```
cp env.local .env.local
```

### Running Biome to lint/format code:
```
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
