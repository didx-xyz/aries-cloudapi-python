#!/bin/bash
source ./env.sh
# ./k6 run --out output-statsd -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true debug.js
xk6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-holders.js
xk6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-invitation.js
xk6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-credentials.js
xk6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-proof.js
xk6 run -e SKIP_DELETE_ISSUERS=false -e SKIP_DELETE_HOLDERS=false delete-holders.js
