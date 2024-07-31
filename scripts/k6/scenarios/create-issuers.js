/* global __ENV, __ITER, __VU */
// Solve Codacy '__ENV' is not defined. error

import { check } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Trend } from "k6/metrics";
import { getBearerToken } from "../libs/auth.js";
import {
  createCredentialDefinition,
  createIssuerTenant,
  deleteTenant,
  getTrustRegistryActor,
  getWalletIdByWalletName,
} from "../libs/functions.js";

const vus = parseInt(__ENV.VUS, 10);
const iterations = parseInt(__ENV.ITERATIONS, 10);
const issuerPrefix = __ENV.ISSUER_PREFIX;
// const holderPrefix = __ENV.HOLDER_PREFIX;

export let options = {
  scenarios: {
    default: {
      executor: "per-vu-iterations",
      vus: vus,
      iterations: iterations,
      maxDuration: "24h",
    },
  },
  setupTimeout: "300s", // Increase the setup timeout to 120 seconds
  teardownTimeout: "120s", // Increase the teardown timeout to 120 seconds
  maxRedirects: 4,
  thresholds: {
    // https://community.grafana.com/t/ignore-http-calls-made-in-setup-or-teardown-in-results/97260/2
    "http_req_duration{scenario:default}": [`max>=0`],
    "http_reqs{scenario:default}": ["count >= 0"],
    "iteration_duration{scenario:default}": ["max>=0"],
  },
  tags: {
    test_run_id: "phased-issuance",
    test_phase: "create-issuers",
  },
};

const testFunctionReqs = new Counter("test_function_reqs");
const mainIterationDuration = new Trend("main_iteration_duration");

// Seed data: Generating a list of options.iterations unique wallet names
const wallets = new SharedArray("wallets", function () {
  const walletsArray = [];
  for (let i = 0; i < options.scenarios.default.iterations * options.scenarios.default.vus; i++) {
    walletsArray.push({
      walletLabel: `${issuerPrefix} ${i}`,
      walletName: `${issuerPrefix}_${i}`,
    });
  }
  return walletsArray;
});

export function setup() {
  const bearerToken = getBearerToken();
  return { bearerToken };
}

const iterationsPerVU = options.scenarios.default.iterations;
// Helper function to calculate the wallet index based on VU and iteration
function getWalletIndex(vu, iter) {
  const walletIndex = (vu - 1) * iterationsPerVU + (iter - 1);
  return walletIndex;
}

export default function (data) {
  const start = Date.now();
  const bearerToken = data.bearerToken;
  const walletIndex = getWalletIndex(__VU, __ITER + 1); // __ITER starts from 0, adding 1 to align with the logic
  const wallet = wallets[walletIndex];
  const credDefTag = wallet.walletName;

  const createIssuerTenantResponse = createIssuerTenant(bearerToken, wallet.walletName);
  check(createIssuerTenantResponse, {
    "Issuer tenant created successfully": (r) => r.status === 200,
  });
  const issuerAccessToken = createIssuerTenantResponse.json().access_token;

  const getTrustRegistryActorResponse = getTrustRegistryActor(wallet.walletName);
  check(getTrustRegistryActorResponse, {
    "Trust Registry Actor Response status code is 200": (r) => {
      if (r.status !== 200) {
        console.error(
          `Unexpected response status while getting trust registry actor for issuer tenant ${wallet.walletName}: ${r.status}`,
        );
        return false;
      } else {
        console.log(`Got trust registry actor for issuer tenant ${wallet.walletName} successfully.`);
        return true;
      }
    },
  });

  // const createCredentialDefinitionResponse = createCredentialDefinition(bearerToken, issuerAccessToken, credDefTag);
  // check(createCredentialDefinitionResponse, {
  //   "Credential definition created successfully": (r) => r.status === 200
  // });

  const end = Date.now();
  const duration = end - start;
  // console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  mainIterationDuration.add(duration);
  testFunctionReqs.add(1);
}

export function teardown(data) {
  const bearerToken = data.bearerToken;

  // // Delete issuer tenants
  if (__ENV.SKIP_DELETE_ISSUERS !== "true") {
    for (const wallet of wallets) {
      const walletId = getWalletIdByWalletName(bearerToken, wallet.walletName);
      const deleteIssuerResponse = deleteTenant(bearerToken, walletId);
      check(deleteIssuerResponse, {
        "Delete Issuer Tenant Response status code is 200": (r) => {
          if (r.status !== 200) {
            console.error(`Unexpected response status while deleting issuer tenant ${walletId}: ${r.status}`);
            return false;
          } else {
            console.log(`Deleted issuer tenant ${walletId} successfully.`);
            return true;
          }
        },
      });
    }
  }
}
