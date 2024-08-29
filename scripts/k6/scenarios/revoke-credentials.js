/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Trend } from "k6/metrics";
import { getBearerToken } from "../libs/auth.js";
import {
  checkRevoked,
  createCredentialDefinition,
  deleteTenant,
  getCredentialDefinitionId,
  getWalletIdByWalletName,
  revokeCredential,
} from "../libs/functions.js";
import { createIssuerIfNotExists } from "../libs/issuerUtils.js";
import { createSchemaIfNotExists } from "../libs/schemaUtils.js";

const vus = Number.parseInt(__ENV.VUS, 10);
const iterations = Number.parseInt(__ENV.ITERATIONS, 10);
const issuerPrefix = __ENV.ISSUER_PREFIX;

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

const inputFilepath = "../output/create-credentials.json";
const data = open(inputFilepath, "r");

const testFunctionReqs = new Counter("test_function_reqs");

const numIssuers = 1;

export function setup() {
  const issuers = [];
  const ids = data.trim().split("\n").map(JSON.parse);
  const bearerToken = getBearerToken();
  for (let i = 0; i < numIssuers; i++) {
    const walletName = `${issuerPrefix}_${i}`;
    const credDefTag = walletName;

    const issuerData = createIssuerIfNotExists(bearerToken, walletName);
    check(issuerData, {
      "Issuer data retrieved successfully": (data) => data !== null && data !== undefined,
    });
    if (!issuerData) {
      console.error(`Failed to create or retrieve issuer for ${walletName}`);
      continue;
    }
    const { issuerWalletId, issuerAccessToken } = issuerData;

    const credentialDefinitionId = getCredentialDefinitionId(bearerToken, issuerAccessToken, credDefTag);
    if (credentialDefinitionId) {
      console.log(`Credential definition already exists for issuer ${walletName} - Skipping creation`);
      issuers.push({
        walletId: issuerWalletId,
        accessToken: issuerAccessToken,
        credentialDefinitionId,
      });
      continue;
    }
    console.warn(`Failed to get credential definition ID for issuer ${walletName}`);
    // console.error(`Response body: ${credentialDefinitionId.body}`);

    const schemaId = createSchemaIfNotExists(governanceBearerToken, schemaName, schemaVersion);
    check(schemaId, {
      "Schema ID is not null": (id) => id !== null && id !== undefined,
    });

    const createCredentialDefinitionResponse = createCredentialDefinition(
      bearerToken,
      issuerAccessToken,
      credDefTag,
      schemaId,
    );
    check(createCredentialDefinitionResponse, {
      "Credential definition created successfully": (r) => r.status === 200,
    });

    if (createCredentialDefinitionResponse.status === 200) {
      const { id: credentialDefinitionId } = JSON.parse(createCredentialDefinitionResponse.body);
      console.log(`Credential definition created successfully for issuer ${walletName}`);
      issuers.push({
        walletId: issuerWalletId,
        accessToken: issuerAccessToken,
        credentialDefinitionId,
      });
    } else {
      console.error(`Failed to create credential definition for issuer ${walletName}`);
    }
  }
  return { bearerToken, ids, issuers }; // eslint-disable-line no-eval
}

const iterationsPerVU = options.scenarios.default.iterations;
// Helper function to calculate the wallet index based on VU and iteration
function getWalletIndex(vu, iter) {
  const walletIndex = (vu - 1) * iterationsPerVU + (iter - 1);
  return walletIndex;
}

export default function (data) {
  const issuers = data.issuers;
  const ids = data.ids;
  const walletIndex = getWalletIndex(__VU, __ITER + 1); // __ITER starts from 0, adding 1 to align with the logic
  const id = ids[walletIndex];

  const issuerIndex = __ITER % numIssuers;
  const issuer = issuers[issuerIndex];
  const revokeCredentialResponse = revokeCredentialAutoPublish(issuer.accessToken, id.credential_exchange_id);
  check(revokeCredentialResponse, {
    "successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while revoking credential: ${r.response}`);
      }
      return true;
    },
  });
  const checkRevokedCredentialResponse = checkRevoked(issuer.accessToken, id.credential_exchange_id);
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
  // sleep(0.2);
  testFunctionReqs.add(1);
}
