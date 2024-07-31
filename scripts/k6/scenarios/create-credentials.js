/* global __ENV, __ITER, __VU */
/* eslint no-undef: "error" */
/* eslint no-console: ["error", { allow: ["warn", "error", "log"] }] */

import { check, sleep } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Trend } from "k6/metrics";
import { getBearerToken } from "../libs/auth.js";
import {
  acceptCredential,
  createCredential,
  createCredentialDefinition,
  deleteTenant,
  getCredentialDefinitionId,
  getCredentialIdByThreadId,
  getWalletIdByWalletName,
  waitForSSEEvent,
} from "../libs/functions.js";
import { createIssuerIfNotExists } from "../libs/issuerUtils.js";
import { createSchemaIfNotExists } from "../libs/schemaUtils.js";

const vus = parseInt(__ENV.VUS, 10);
const iterations = parseInt(__ENV.ITERATIONS, 10);
const issuerPrefix = __ENV.ISSUER_PREFIX;

export let options = {
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

// const specificFunctionReqs = new Counter('specific_function_reqs');
const testFunctionReqs = new Counter("test_function_reqs");
// const mainIterationDuration = new Trend('main_iteration_duration');

// Seed data: Generating a list of options.iterations unique wallet names
// const wallets = new SharedArray('wallets', function() {
//   const walletsArray = [];
//   for (let i = 0; i < options.iterations; i++) {
//     walletsArray.push({
//       wallet_label: `xk6 holder ${i}`,
//       wallet_name: `xk6_wallet_${i}`
//     });
//   }
//   return walletsArray;
// });

const numIssuers = 1;
let issuers = [];

export function setup() {
  const bearerToken = getBearerToken();
  const issuers = [];

  const holders = data.trim().split("\n").map(JSON.parse);

  // // Example usage of the loaded data
  // holders.forEach((holderData) => {
  //   console.log(`Processing wallet ID: ${holderData.wallet_id}`);
  //   // Your test logic here, e.g., make HTTP requests using the holderData
  // });

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
    } else {
      console.warn(`Failed to get credential definition ID for issuer ${walletName}`);
      // console.error(`Response body: ${credentialDefinitionId.body}`);
    }

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

  const issuerIndex = __ITER % numIssuers;
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

  const { thread_id: threadId } = JSON.parse(createCredentialResponse.body);

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

  // specificFunctionReqs.add(1, { my_custom_tag: 'specific_function' });

  // const end = Date.now();
  // const duration = end - start;
  // console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  // mainIterationDuration.add(duration);
  // sleep(1);
  testFunctionReqs.add(1);
}

export function teardown(data) {
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;
  const wallets = data.holders;

  // console.log(__ENV.SKIP_DELETE_ISSUERS)

  if (__ENV.SKIP_DELETE_ISSUERS !== "true") {
    for (const issuer of issuers) {
      const deleteIssuerResponse = deleteTenant(bearerToken, issuer.walletId);
      check(deleteIssuerResponse, {
        "Delete Issuer Tenant Response status code is 200": (r) => {
          if (r.status !== 200) {
            console.error(`Unexpected response status while deleting issuer tenant ${issuer.walletId}: ${r.status}`);
            return false;
          } else {
            console.log(`Deleted issuer tenant ${issuer.walletId} successfully.`);
            return true;
          }
        },
      });
    }
  } else {
    console.log("Skipping deletion of issuer tenants.");
  }
  // // Delete holder tenants
  if (__ENV.SKIP_DELETE_HOLDERS !== "true") {
    for (const wallet of wallets) {
      const walletId = getWalletIdByWalletName(bearerToken, wallet.wallet_name);
      const deleteHolderResponse = deleteTenant(bearerToken, walletId);
      check(deleteHolderResponse, {
        "Delete Holder Tenant Response status code is 200": (r) => {
          if (r.status !== 200) {
            console.error(`Unexpected response status while deleting holder tenant ${walletId}: ${r.status}`);
            return false;
          } else {
            console.log(`Deleted holder tenant ${walletId} successfully.`);
            return true;
          }
        },
      });
    }
  } else {
    console.log("Skipping deletion of holder tenants.");
  }
}
