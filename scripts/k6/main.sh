#!/bin/bash
source ./env.sh
# ./k6 run --out output-statsd -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true debug.js
./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-holders.js
./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-invitation.js
./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-credentials.js
./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-proof.js
./k6 run -e SKIP_DELETE_ISSUERS=false -e SKIP_DELETE_HOLDERS=false delete-holders.js
