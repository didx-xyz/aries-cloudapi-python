/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { check } from "k6";
import { Counter } from "k6/metrics";
import { getBearerToken } from "../libs/auth.js";
import {
  acceptProofRequest,
  getProof,
  getProofIdByThreadId,
  getProofIdCredentials,
  sendProofRequest,
  waitForSSEEventReceived,
  waitForSSEProofDone,
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
    test_phase: "create-proofs",
  },
};

const inputFilepath = "../output/create-invitation.json";
const data = open(inputFilepath, "r");

// const specificFunctionReqs = new Counter('specific_function_reqs');
const testFunctionReqs = new Counter("test_function_reqs");
// const mainIterationDuration = new Trend('main_iteration_duration');

export function setup() {
  const bearerToken = getBearerToken();

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
  // const sendProofRequestResponse = sendProofRequest(issuer.accessToken, wallet.issuer_connection_id);
  let sendProofRequestResponse;
  try {
    sendProofRequestResponse = sendProofRequest(issuer.accessToken, wallet.issuer_connection_id);
  } catch (error) {
    // console.error(`Error creating credential: ${error.message}`);
    sendProofRequestResponse = { status: 500, response: error.message };
  }
  check(sendProofRequestResponse, {
    "Proof request sent successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while sending proof request: ${r.response}`);
      }
      return true;
    },
  });

  const { thread_id: threadId } = JSON.parse(sendProofRequestResponse.body);

  const waitForSSEEventReceivedResponse = waitForSSEEventReceived(wallet.access_token, wallet.wallet_id, threadId);
  check(waitForSSEEventReceivedResponse, {
    "SSE Event received successfully: request-recevied": (r) => {
      if (!r) {
        throw new Error("SSE event was not received successfully");
      }
      return true;
    },
  });

  // TODO: return object and add check for the response
  const proofId = getProofIdByThreadId(wallet.access_token, threadId);
  const referent = getProofIdCredentials(wallet.access_token, proofId);

  const acceptProofResponse = acceptProofRequest(wallet.access_token, proofId, referent);
  check(acceptProofResponse, {
    "Proof accepted successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while accepting proof: ${r.response}`);
      }
      return true;
    },
  });

  const waitForSSEProofDoneRequest = waitForSSEProofDone(issuer.accessToken, issuer.walletId, threadId);
  check(waitForSSEProofDoneRequest, {
    "SSE Proof Request state: done": (r) => {
      if (!r) {
        throw new Error("SSE proof done was not successful");
      }
      return true;
    },
  });

  // const getProofResponse = getProof(issuer.accessToken, wallet.issuer_connection_id, threadId );
  let getProofResponse;
  try {
    getProofResponse = getProof(issuer.accessToken, wallet.issuer_connection_id, threadId);
  } catch (error) {
    // console.error(`Error creating credential: ${error.message}`);
    getProofResponse = { status: 500, response: error.message };
  }

  const verifiedCheck = (r) => {
    if (r.status !== 200) {
      throw new Error(`Unexpected response while getting proof: ${r.response}`);
    }
    const responseBody = JSON.parse(r.body);
    if (responseBody[0].verified !== true) {
      throw new Error(`Credential is not verified. Current verification status: ${responseBody[0].verified}`);
    }
    return true;
  };

  const unverifiedCheck = (r) => {
    if (r.status !== 200) {
      throw new Error(`Unexpected response while getting proof: ${r.response}`);
    }
    const responseBody = JSON.parse(r.body);
    if (responseBody[0].verified !== false) {
      throw new Error(`Credential is not unverified. Current verification status: ${responseBody[0].verified}`);
    }
    return true;
  };

  check(getProofResponse, {
    [__ENV.IS_REVOKED === "true" ? "Proof received and unverified" : "Proof received and verified"]:
      __ENV.IS_REVOKED === "true" ? unverifiedCheck : verifiedCheck,
  });

  testFunctionReqs.add(1);
}
