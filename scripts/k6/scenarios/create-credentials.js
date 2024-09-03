/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { check, sleep } from "k6";
import { Counter, Trend } from "k6/metrics";
import file from "k6/x/file";
import { getBearerToken } from "../libs/auth.js";
import {
  acceptCredential,
  createCredential,
  getCredentialIdByThreadId,
  waitForSSEEvent,
} from "../libs/functions.js";
import { bootstrapIssuer } from "../libs/setup.js";

const vus = Number.parseInt(__ENV.VUS, 10);
const iterations = Number.parseInt(__ENV.ITERATIONS, 10);
const issuerPrefix = __ENV.ISSUER_PREFIX;
const schemaName = __ENV.SCHEMA_NAME;
const schemaVersion = __ENV.SCHEMA_VERSION;

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
    // 'specific_function_reqs{my_custom_tag:specific_function}': ['count>=0'],
    // 'specific_function_reqs{scenario:default}': ['count>=0'],
  },
  tags: {
    test_run_id: "phased-issuance",
    test_phase: "create-credentials",
  },
};

const inputFilepath = "../output/create-invitation.json";
const data = open(inputFilepath, "r");
const outputFilepath = "output/create-credentials.json";

// const specificFunctionReqs = new Counter('specific_function_reqs');
const testFunctionReqs = new Counter("test_function_reqs");
// const mainIterationDuration = new Trend('main_iteration_duration');

export function setup() {
  const bearerToken = getBearerToken();

  file.writeString(outputFilepath, "");
  const holders = data.trim().split("\n").map(JSON.parse);

  const walletName = issuerPrefix;
  const credDefTag = walletName;
  const issuers = bootstrapIssuer(walletName, credDefTag, schemaName, schemaVersion);

  if (!issuers || issuers.length === 0) {
    console.error("Failed to bootstrap issuers.");
  }

  return { bearerToken, issuers, holders };
}

const iterationsPerVU = options.scenarios.default.iterations;
// Helper function to calculate the wallet index based on VU and iteration
function getWalletIndex(vu, iter) {
  const walletIndex = (vu - 1) * iterationsPerVU + (iter - 1);
  return walletIndex;
}

//random number between 0 and 100 (including 0 and 100 as options)
function getRandomInt() {
  return Math.floor(Math.random() * 101);
}

export default function (data) {
  // const start = Date.now();
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;
  const holders = data.holders;
  const walletIndex = getWalletIndex(__VU, __ITER + 1); // __ITER starts from 0, adding 1 to align with the logic
  const wallet = holders[walletIndex];

  const issuerIndex = 0;
  const issuer = issuers[issuerIndex];

  // console.log(`isser.accessToken: ${issuer.accessToken}`);
  // console.log(`issuer.credentialDefinitionId: ${issuer.credentialDefinitionId}`);
  // console.log(`wallet.issuer_connection_id: ${wallet.issuer_connection_id}`);

  // const createCredentialResponse = createCredential(bearerToken, issuer.accessToken, issuer.credentialDefinitionId, wallet.issuer_connection_id);
  // check(createCredentialResponse, {
  //   "Credential created successfully": (r) => {
  //     if (r.status !== 200) {
  //       throw new Error(`Unexpected response while creating credential: ${r.response}`);
  //     }
  //     return true;
  //   }
  // });

  let createCredentialResponse;
  try {
    createCredentialResponse = createCredential(
      bearerToken,
      issuer.accessToken,
      issuer.credentialDefinitionId,
      wallet.issuer_connection_id,
    );
  } catch (error) {
    // console.error(`Error creating credential: ${error.message}`);
    createCredentialResponse = { status: 500, response: error.message };
  }

  check(createCredentialResponse, {
    "Credential created successfully": (r) => {
      if (r.status !== 200) {
        console.error(`Unexpected response while creating credential: ${r.response}`);
        return false;
      }
      return true;
    },
  });

  const { thread_id: threadId, credential_exchange_id: credentialExchangeId } = JSON.parse(
    createCredentialResponse.body,
  );

  // console.log(`Thread ID: ${threadId}`);
  // console.log(`Holer access token: ${wallet.holder_access_token}`);
  // console.log(`Wallet ID: ${wallet.wallet_id}`);

  const waitForSSEEventResponse = waitForSSEEvent(wallet.access_token, wallet.wallet_id, threadId);
  check(waitForSSEEventResponse, {
    "SSE request received successfully: request-received": (r) => {
      if (!r) {
        throw new Error("SSE event was not received successfully");
      }
      return true;
    },
  });

  const credentialId = getCredentialIdByThreadId(wallet.access_token, threadId);

  const acceptCredentialResponse = acceptCredential(wallet.access_token, credentialId);
  check(acceptCredentialResponse, {
    "Credential accepted successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while accepting credential: ${r.response}`);
      }
      return true;
    },
  });

  const issuerData = JSON.stringify({
    credential_exchange_id: credentialExchangeId,
  });
  file.appendString(outputFilepath, `${issuerData}\n`);

  // specificFunctionReqs.add(1, { my_custom_tag: 'specific_function' });

  // const end = Date.now();
  // const duration = end - start;
  // console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  // mainIterationDuration.add(duration);
  // sleep(1);
  testFunctionReqs.add(1);
}
