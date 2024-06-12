#!/bin/bash
source ./env.sh
# ./k6 run --out output-statsd -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true debug.js
./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-holders.js
./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=false create-invitation.js
# ./k6 run -e SKIP_DELETE_ISSUERS=true -e SKIP_DELETE_HOLDERS=true create-credentials.js
