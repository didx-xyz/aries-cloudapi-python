/* global __ENV, __ITER, __VU */
/* eslint no-undef: "error" */
/* eslint no-console: ["error", { allow: ["warn", "error", "log"] }] */

import { check } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Trend } from "k6/metrics";
import { getBearerToken } from "./auth.js";
import {
  acceptCredential,
  acceptInvitation,
  createCredential,
  createCredentialDefinition,
  createInvitation,
  createIssuerTenant,
  createTenant,
  deleteTenant,
  getAccessTokenByWalletId,
  getCredentialDefinitionId,
  getCredentialIdByThreadId,
  getWalletIdByWalletName,
  waitForSSEEvent,
  waitForSSEEventConnection,
} from "./tenant.js";

export const options = {
  vus: 2, // number of VUs to run
  iterations: 2, // total number of iterations (global)
  maxRedirects: 4,
  thresholds: {
    // https://community.grafana.com/t/ignore-http-calls-made-in-setup-or-teardown-in-results/97260/2
    "http_req_duration{scenario:default}": ["max>=0"],
    "http_reqs{scenario:default}": ["count >= 0"],
    "iteration_duration{scenario:default}": ["max>=0"],
    "specific_function_reqs{my_custom_tag:specific_function}": ["count>=0"],
    "specific_function_reqs{scenario:default}": ["count>=0"],
  },
  tags: {
    test_run_id: "sequential-issuance",
  },
};

const specificFunctionReqs = new Counter("specific_function_reqs");
const mainIterationDuration = new Trend("main_iteration_duration");

// Seed data: Generating a list of options.iterations unique wallet names
const wallets = new SharedArray("wallets", () => {
  const walletsArray = [];
  for (let i = 0; i < options.iterations; i++) {
    walletsArray.push({
      wallet_label: `xk6 holder ${i}`, // eslint-disable-line camelcase
      wallet_name: `xk6_wallet_${i}`, // eslint-disable-line camelcase
    });
  }
  return walletsArray;
});

const numIssuers = 1;
const issuers = [];

export function setup() {
  const bearerToken = getBearerToken();
  const issuers = [];

  for (let i = 0; i < numIssuers; i++) {
    const walletName = `k6issuer_${i}`;
    const credDefTag = walletName;

    let issuerAccessToken;
    let issuerWalletId;

    issuerWalletId = getWalletIdByWalletName(bearerToken, walletName);
    if (issuerWalletId !== null) {
      // Retrieve the access token using the wallet ID
      issuerAccessToken = getAccessTokenByWalletId(bearerToken, issuerWalletId);
      if (typeof issuerAccessToken === "string") {
        // Access token retrieved successfully
        console.log(`Access token retrieved via wallet ID for ${issuerWalletId}`);
      } else {
        console.error(`Failed to retrieve access token for wallet ID ${issuerWalletId}`);
        console.error(`Response body: ${issuerAccessToken}`);
        continue;
      }
    } else {
      try {
        const createIssuerTenantResponse = createIssuerTenant(bearerToken, walletName);
        check(createIssuerTenantResponse, {
          "Issuer tenant created successfully": (r) => r.status === 200,
        });
        const tenantData = JSON.parse(createIssuerTenantResponse.body);
        issuerWalletId = tenantData.wallet_id;
        issuerAccessToken = tenantData.access_token;
      } catch (error) {
        console.error(`Error creating issuer tenant for ${walletName}:`, error);
        continue;
      }
    }

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

    const createCredentialDefinitionResponse = createCredentialDefinition(bearerToken, issuerAccessToken, credDefTag);
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

  return { bearerToken, issuers };
}

// Helper function to calculate the wallet index based on VU and iteration
function getWalletIndex(vu, iter) {
  const iterationsPerVU = Math.floor(options.iterations / options.vus);
  const startIndex = (vu - 1) * iterationsPerVU;
  return startIndex + (iter % iterationsPerVU);
}

export default function (data) {
  const start = Date.now();
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;
  const walletIndex = getWalletIndex(__VU, __ITER);
  const wallet = wallets[walletIndex];
  const issuerIndex = __ITER % numIssuers;
  const issuer = issuers[issuerIndex];

  const createTenantResponse = createTenant(bearerToken, wallet);
  check(createTenantResponse, {
    "Create Tenant Response status code is 200": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response status: ${r.status}`);
      }
      return true;
    },
  });
  const { wallet_id: walletId, access_token: holderAccessToken } = JSON.parse(createTenantResponse.body);

  const createInvitationResponse = createInvitation(bearerToken, issuer.accessToken);
  check(createInvitationResponse, {
    "Invitation created successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response status while create invitation: ${r.status}`);
      }
      return true;
    },
  });
  const { invitation: invitationObj, connection_id: issuerConnectionId } = JSON.parse(createInvitationResponse.body);

  const acceptInvitationResponse = acceptInvitation(holderAccessToken, invitationObj);
  check(acceptInvitationResponse, {
    "Invitation accepted successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while accepting invitation: ${r.response}`);
      }
      return true;
    },
  });

  const { connection_id: holderInvitationConnectionId } = JSON.parse(acceptInvitationResponse.body);

  const waitForSSEEventConnectionResponse = waitForSSEEventConnection(
    holderAccessToken,
    walletId,
    holderInvitationConnectionId,
  );
  check(waitForSSEEventConnectionResponse, {
    "SSE Event received successfully: connection-ready": (r) => {
      if (!r) {
        throw new Error("SSE event was not received successfully");
      }
      return true;
    },
  });

  const createCredentialResponse = createCredential(
    bearerToken,
    issuer.accessToken,
    issuer.credentialDefinitionId,
    issuerConnectionId,
  );
  check(createCredentialResponse, {
    "Credential created successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while creating credential: ${r.response}`);
      }
      return true;
    },
  });

  const { thread_id: threadId } = JSON.parse(createCredentialResponse.body);

  const waitForSSEEventResponse = waitForSSEEvent(holderAccessToken, walletId, threadId);
  check(waitForSSEEventResponse, {
    "SSE Event received successfully: offer-received": (r) => {
      if (!r) {
        throw new Error("SSE event was not received successfully");
      }
      return true;
    },
  });

  const credentialId = getCredentialIdByThreadId(holderAccessToken, threadId);

  const acceptCredentialResponse = acceptCredential(holderAccessToken, credentialId);
  check(acceptCredentialResponse, {
    "Credential accepted successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while accepting credential: ${r.response}`);
      }
      return true;
    },
  });

  specificFunctionReqs.add(1, { my_custom_tag: "specific_function" });

  const end = Date.now();
  const duration = end - start;
  console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  mainIterationDuration.add(duration);
}

export function teardown(data) {
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;

  if (__ENV.SKIP_DELETE_ISSUERS !== "true") {
    for (const issuer of issuers) {
      const deleteIssuerResponse = deleteTenant(bearerToken, issuer.walletId);
      check(deleteIssuerResponse, {
        "Delete Issuer Tenant Response status code is 200": (r) => {
          if (r.status !== 200) {
            console.error(`Unexpected response status while deleting issuer tenant ${issuer.walletId}: ${r.status}`);
            return false;
          }
          console.log(`Deleted issuer tenant ${issuer.walletId} successfully.`);
          return true;
        },
      });
    }
  } else {
    console.log("Skipping deletion of issuer tenants.");
  }
  // // Delete holder tenants
  for (const wallet of wallets) {
    const walletId = getWalletIdByWalletName(bearerToken, wallet.wallet_name);
    const deleteHolderResponse = deleteTenant(bearerToken, walletId);
    check(deleteHolderResponse, {
      "Delete Holder Tenant Response status code is 200": (r) => {
        if (r.status !== 200) {
          console.error(`Unexpected response status while deleting holder tenant ${walletId}: ${r.status}`);
          return false;
        }
        console.log(`Deleted holder tenant ${walletId} successfully.`);
        return true;
      },
    });
  }
}
