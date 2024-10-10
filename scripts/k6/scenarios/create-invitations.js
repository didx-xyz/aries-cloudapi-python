/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { check } from "k6";
import { Counter, Trend } from "k6/metrics";
import file from "k6/x/file";
import { getBearerToken } from "../libs/auth.js";
import {
  acceptInvitation,
  createInvitation,
  genericWaitForSSEEvent,
  getWalletIndex,
} from "../libs/functions.js";
import { bootstrapIssuer } from "../libs/setup.js";
// import bootstrapIssuer from "./bootstrap-issuer.js";

const vus = Number.parseInt(__ENV.VUS, 10);
const iterations = Number.parseInt(__ENV.ITERATIONS, 10);
const issuerPrefix = __ENV.ISSUER_PREFIX;
const schemaName = __ENV.SCHEMA_NAME;
const schemaVersion = __ENV.SCHEMA_VERSION;
const numIssuers = __ENV.NUM_ISSUERS;

export const options = {
  scenarios: {
    default: {
      executor: "per-vu-iterations",
      vus,
      iterations,
      maxDuration: "24h",
    },
  },
  setupTimeout: "120s", // Increase the setup timeout to 120 seconds
  teardownTimeout: "120s", // Increase the teardown timeout to 120 seconds
  maxRedirects: 4,
  thresholds: {
    // https://community.grafana.com/t/ignore-http-calls-made-in-setup-or-teardown-in-results/97260/2
    "http_req_duration{scenario:default}": ["max>=0"],
    "http_reqs{scenario:default}": ["count >= 0"],
    "http_reqs{my_custom_tag:specific_function}": ["count>=0"],
    "iteration_duration{scenario:default}": ["max>=0"],
    checks: ["rate==1"],
    // 'test_function_reqs{my_custom_tag:specific_function}': ['count>=0'],
    // 'test_function_reqs{scenario:default}': ['count>=0'],
    // 'custom_duration{step:getAccessTokenByWalletId}': ['avg>=0'],
  },
  tags: {
    test_run_id: "phased-issuance",
    test_phase: "create-invitation",
  },
};

const testFunctionReqs = new Counter("test_function_reqs");
const mainIterationDuration = new Trend("main_iteration_duration");

const inputFilepath = "../output/create-holders.json";
const data = open(inputFilepath, "r");
const outputFilepath = "output/create-invitation.json";

export function setup() {
  const bearerToken = getBearerToken();
  const holders = data.trim().split("\n").map(JSON.parse);
  file.writeString(outputFilepath, "");

  const walletName = issuerPrefix;
  const credDefTag = walletName;
  const issuers = bootstrapIssuer(
    numIssuers,
    walletName,
    credDefTag,
    schemaName,
    schemaVersion
  );

  if (!issuers || issuers.length === 0) {
    console.error("Failed to bootstrap issuers.");
  }

  return { bearerToken, issuers, holders };
}

function getIssuerIndex(vu, iter) {
  const numIssuers = __ENV.NUM_ISSUERS;
  return (vu + iter - 2) % numIssuers;
}

const vuStartTimes = {};
const vuEndTimes = {};

export default function (data) {
  if (__ITER === 0) {
    vuStartTimes[__VU] = Date.now();
  }
  const start = Date.now();
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;
  const walletIndex = getWalletIndex(__VU, __ITER, iterations);

  // console.log(`VU: ${__VU}, Iteration: ${__ITER}, Wallet Index: ${walletIndex}`);

  const holders = data.holders;
  const wallet = holders[walletIndex];

  // const issuerIndex = __ITER % numIssuers;
  const issuerIndex = getIssuerIndex(__VU, __ITER + 1);
  const issuer = issuers[issuerIndex];

  // console.log(`VU: ${__VU}, Iteration: ${__ITER}, Wallet Index: ${walletIndex}, Issuer Index: ${issuerIndex}, Issuer Wallet ID: ${issuer.walletId}`);

  const createInvitationResponse = createInvitation(
    bearerToken,
    issuer.accessToken
  );
  check(createInvitationResponse, {
    "Invitation created successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(
          `Unexpected response status while create invitation: ${r.status}`
        );
      }
      return true;
    },
  });
  const { invitation: invitationObj, connection_id: issuerConnectionId } =
    JSON.parse(createInvitationResponse.body);

  const acceptInvitationResponse = acceptInvitation(
    wallet.access_token,
    invitationObj
  );
  check(acceptInvitationResponse, {
    "Invitation accepted successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(
          `Unexpected response while accepting invitation: ${r.response}`
        );
      }
      return true;
    },
  });

  const { connection_id: holderInvitationConnectionId } = JSON.parse(
    acceptInvitationResponse.body
  );

  const waitForSSEEventConnectionResponse = genericWaitForSSEEvent({
    accessToken: wallet.access_token,
    walletId: wallet.wallet_id,
    threadId: holderInvitationConnectionId,
    eventType: "completed",
    sseUrlPath: "connections/connection_id",
    topic: "connections",
    expectedState: "completed",
    maxDuration: 10,
    sseTag: "connection_ready",
  });

  check(waitForSSEEventConnectionResponse, {
    "SSE Event received successfully: connection-ready": (r) => {
      if (!r) {
        throw new Error("SSE connection event was not received successfully");
      }
      return true;
    },
  });

  // testFunctionReqs.add(1, { my_custom_tag: 'specific_function' });

  testFunctionReqs.add(1);

  const holderData = JSON.stringify({
    wallet_label: wallet.wallet_label,
    wallet_name: wallet.wallet_name,
    wallet_id: wallet.wallet_id,
    access_token: wallet.access_token,
    connection_id: holderInvitationConnectionId,
    issuer_connection_id: issuerConnectionId,
    issuer_wallet_name: issuer.walletName,
    issuer_wallet_id: issuer.walletId,
    issuer_access_token: issuer.accessToken,
    issuer_credential_definition_id: issuer.credentialDefinitionId,
  });
  file.appendString(outputFilepath, `${holderData}\n`);

  const end = Date.now();
  const duration = end - start;
  // console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  mainIterationDuration.add(duration);
}
