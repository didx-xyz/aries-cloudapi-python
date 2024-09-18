/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { check } from "k6";
import { Counter } from "k6/metrics";
import { getBearerToken } from "../libs/auth.js";
import {
  checkRevoked,
  revokeCredentialAutoPublish,
} from "../libs/functions.js";
import { bootstrapIssuer } from "../libs/setup.js";

const inputFilepath = "../output/create-credentials.json";
const data = open(inputFilepath, "r");

const vus = Number.parseInt(__ENV.VUS, 10);
const iterations = Number.parseInt(__ENV.ITERATIONS, 10);
const issuerPrefix = __ENV.ISSUER_PREFIX;
const schemaName = __ENV.SCHEMA_NAME;
const schemaVersion = __ENV.SCHEMA_VERSION;
const testFunctionReqs = new Counter("test_function_reqs");

export const options = {
  scenarios: {
    default: {
      executor: "per-vu-iterations",
      vus,
      iterations,
      maxDuration: "24h",
    },
  },
  setupTimeout: "180s", // Increase the setup timeout to 120 seconds
  teardownTimeout: "180s", // Increase the teardown timeout to 120 seconds
  maxRedirects: 4,
  thresholds: {
    // https://community.grafana.com/t/ignore-http-calls-made-in-setup-or-teardown-in-results/97260/2
    "http_req_duration{scenario:default}": ["max>=0"],
    "http_reqs{scenario:default}": ["count >= 0"],
    "iteration_duration{scenario:default}": ["max>=0"],
    checks: ["rate==1"],
  },
  tags: {
    test_run_id: "phased-issuance",
    test_phase: "revoke-credentials",
  },
};

export function setup() {
  const tenants = data.trim().split("\n").map(JSON.parse);
  const bearerToken = getBearerToken();
  return { bearerToken, tenants }; // eslint-disable-line no-eval
}

const iterationsPerVU = options.scenarios.default.iterations;
// Helper function to calculate the wallet index based on VU and iteration
function getWalletIndex(vu, iter) {
  const walletIndex = (vu - 1) * iterationsPerVU + (iter - 1);
  return walletIndex;
}

export default function (data) {
  const tenants = data.tenants;
  const walletIndex = getWalletIndex(__VU, __ITER + 1); // __ITER starts from 0, adding 1 to align with the logic
  const wallet = tenants[walletIndex];

  const issuerIndex = 0;
  const issuer = issuers[issuerIndex];
  const revokeCredentialResponse = revokeCredentialAutoPublish(wallet.issuer_access_token, wallet.credential_exchange_id);
  check(revokeCredentialResponse, {
    "Credential revoked successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while revoking credential: ${r.response}`);
      }
      return true;
    },
  });
  const checkRevokedCredentialResponse = checkRevoked(wallet.issuer_access_token, wallet.credential_exchange_id);
  check(checkRevokedCredentialResponse, {
    "Credential state is revoked": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while checking if credential is revoked: ${r.status}`);
      }
      const responseBody = JSON.parse(r.body);
      if (responseBody.state !== "revoked") {
        throw new Error(`Credential state is not revoked. Current state: ${responseBody.state}`);
      }
      return true;
    },
  });
  testFunctionReqs.add(1);
}
