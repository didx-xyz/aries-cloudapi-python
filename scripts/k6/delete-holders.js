/* global __ENV */
/* eslint no-undef: "error" */
/* eslint no-console: ["error", { allow: ["warn", "error", "log"] }] */

import { sleep, check } from "k6";
import { SharedArray } from "k6/data";
import { getBearerToken } from "./auth.js";
import { Trend, Counter } from "k6/metrics";
import {
  getWalletIdByWalletName,
  deleteTenant,
} from "./tenant.js";

const vus = parseInt(__ENV.VUS, 10);
const iterations = parseInt(__ENV.ITERATIONS, 10);
const holderPrefix = __ENV.HOLDER_PREFIX;

export let options = {
  scenarios: {
    default: {
      executor: "per-vu-iterations",
      vus,
      iterations,
      maxDuration: "120s",
    },
  },
  setupTimeout: "180s", // Increase the setup timeout to 120 seconds
  teardownTimeout: "120s", // Increase the teardown timeout to 120 seconds
  maxRedirects: 4,
  thresholds: { //https://community.grafana.com/t/ignore-http-calls-made-in-setup-or-teardown-in-results/97260/2
    "http_req_duration{scenario:default}": ["max>=0"],
    "http_reqs{scenario:default}": ["count >= 0"],
    "iteration_duration{scenario:default}": ["max>=0"],
    "checks": ["rate==1"]
  },
  tags: {
    test_run_id: "phased-issuance",
    test_phase: "delete-holders",
  },
};

const testFunctionReqs = new Counter("test_function_reqs");

// Seed data: Generating a list of options.iterations unique wallet names
const wallets = new SharedArray("wallets", function() {
  const walletsArray = [];
  for (let i = 0; i < options.scenarios.default.iterations * options.scenarios.default.vus; i++) {
    walletsArray.push({
      wallet_label: `${holderPrefix} ${i}`,
      wallet_name: `${holderPrefix}_${i}`
    });
  }
  return walletsArray;
});

const numIssuers = 1;
let issuers = [];
const filepath = "output/create-holders.json";

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

export default function(data) {
  const bearerToken = data.bearerToken;
  const walletIndex = getWalletIndex(__VU, __ITER + 1); // __ITER starts from 0, adding 1 to align with the logic
  const wallet = wallets[walletIndex];

  const walletId =  getWalletIdByWalletName(bearerToken, wallet.wallet_name);
  const deleteHolderResponse = deleteTenant(bearerToken, walletId);
  check (deleteHolderResponse, {
    "Delete Holder Tenant Response status code is 200": (r) => {
      if (r.status !== 200) {
        console.error(`Unexpected response status while deleting holder tenant ${walletId}: ${r.status}`);
        return false;
      } else {
        // console.log(`Deleted holder tenant ${walletId} successfully.`);
        return true;
      }
    }
  });
  testFunctionReqs.add(1);
}
