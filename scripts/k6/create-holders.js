import { check } from 'k6';
import { SharedArray } from 'k6/data';
import { getBearerToken } from './auth.js';
import { Trend, Counter } from 'k6/metrics';
import file from 'k6/x/file';
import {
  createTenant,
  getWalletIdByWalletName,
  getAccessTokenByWalletId,
  deleteTenant,
  createIssuerTenant,
  createInvitation,
  acceptInvitation,
  createCredential,
  acceptCredential,
  createCredentialDefinition,
  getCredentialIdByThreadId,
  waitForSSEEvent,
  waitForSSEEventConnection,
  getCredentialDefinitionId
} from './tenant.js';

const vus = parseInt(__ENV.VUS);
const iterations = parseInt(__ENV.ITERATIONS);

// vus: vus, // number of VUs to run
// iterations: iterations, // total number of iterations (global)

export let options = {
  scenarios: {
    default: {
      executor: 'per-vu-iterations',
      vus: vus,
      iterations: iterations,
      maxDuration: '120s',
    },
  },
  setupTimeout: '120s', // Increase the setup timeout to 120 seconds
  teardownTimeout: '120s', // Increase the teardown timeout to 120 seconds
  maxRedirects: 4,
  thresholds: { //https://community.grafana.com/t/ignore-http-calls-made-in-setup-or-teardown-in-results/97260/2
    'http_req_duration{scenario:default}': [`max>=0`],
    'http_reqs{scenario:default}': ['count >= 0'],
    'iteration_duration{scenario:default}': ['max>=0'],
    // 'specific_function_reqs{my_custom_tag:specific_function}': ['count>=0'],
    // 'specific_function_reqs{scenario:default}': ['count>=0'],
  },
  tags: {
    test_run_id: 'phased-issuance',
    phase: 'create-holders',
  },
};

const specificFunctionReqs = new Counter('specific_function_reqs');
const mainIterationDuration = new Trend('main_iteration_duration');

// Seed data: Generating a list of options.iterations unique wallet names
const wallets = new SharedArray('wallets', function() {
  const walletsArray = [];
  for (let i = 0; i < options.scenarios.default.iterations * options.scenarios.default.vus; i++) {
    walletsArray.push({
      wallet_label: `k6 holder ${i}`,
      wallet_name: `k6_wallet_${i}`
    });
  }
  return walletsArray;
});

const numIssuers = 1;
let issuers = [];
const filepath = 'output/create-holders.json';

export function setup() {
  const bearerToken = getBearerToken();
  const issuers = [];

  file.writeString(filepath, '');

  for (let i = 0; i < numIssuers; i++) {
    const walletName = `k6issuer_${i}`;
    const credDefTag = walletName;

    let issuerAccessToken;
    let issuerWalletId

    issuerWalletId = getWalletIdByWalletName(bearerToken, walletName);
    if (issuerWalletId !== null) {
      // Retrieve the access token using the wallet ID
      issuerAccessToken = getAccessTokenByWalletId(bearerToken, issuerWalletId);
      if (typeof issuerAccessToken === 'string') {
        // Access token retrieved successfully
        console.log(`Access token retrieved for wallet ID ${issuerWalletId}`);
      } else {
        console.error(`Failed to retrieve access token for wallet ID ${issuerWalletId}`);
        console.error(`Response body: ${issuerAccessToken}`);
        continue;
      }
    } else {
      try {
        const createIssuerTenantResponse = createIssuerTenant(bearerToken, walletName);
        check(createIssuerTenantResponse, {
          "Issuer tenant created successfully": (r) => r.status === 200
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
        credentialDefinitionId: credentialDefinitionId
      });
      continue;
    } else {
      console.warn(`Failed to get credential definition ID for issuer ${walletName}`);
      // console.error(`Response body: ${credentialDefinitionId.body}`);
    }

    const createCredentialDefinitionResponse = createCredentialDefinition(bearerToken, issuerAccessToken, credDefTag);
    check(createCredentialDefinitionResponse, {
      "Credential definition created successfully": (r) => r.status === 200
    });

    if (createCredentialDefinitionResponse.status === 200) {
      const { id: credentialDefinitionId } = JSON.parse(createCredentialDefinitionResponse.body);
      console.log(`Credential definition created successfully for issuer ${walletName}`);
      issuers.push({
        walletId: issuerWalletId,
        accessToken: issuerAccessToken,
        credentialDefinitionId: credentialDefinitionId
      });
    } else {
      console.error(`Failed to create credential definition for issuer ${walletName}`);
    }
  }

  return { bearerToken, issuers };
}

const iterationsPerVU = options.scenarios.default.iterations;
// Helper function to calculate the wallet index based on VU and iteration
function getWalletIndex(vu, iter) {
  const walletIndex = (vu - 1) * iterationsPerVU + (iter - 1);
  return walletIndex;
}

export default function(data) {
  const start = Date.now();
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;
  const walletIndex = getWalletIndex(__VU, __ITER + 1); // __ITER starts from 0, adding 1 to align with the logic
  const wallet = wallets[walletIndex];

  const createTenantResponse = createTenant(bearerToken, wallet);
  check(createTenantResponse, {
    "Create Tenant Response status code is 200": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response status: ${r.status}`);
      }
      return true;
    }
  });
  const { wallet_id: walletId, access_token: holderAccessToken } = JSON.parse(createTenantResponse.body);

  specificFunctionReqs.add(1, { my_custom_tag: 'specific_function' });

  const holderData = JSON.stringify({
    wallet_label: wallet.wallet_label,
    wallet_name: wallet.wallet_name,
    wallet_id: walletId,
    access_token: holderAccessToken,
  });
  file.appendString(filepath, holderData + '\n');

  const end = Date.now();
  const duration = end - start;
  console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  mainIterationDuration.add(duration);
}

export function teardown(data) {
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;

  console.log(__ENV.SKIP_DELETE_ISSUERS)

  if (__ENV.SKIP_DELETE_ISSUERS !== 'true') {
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
        }
      });
    }
  } else {
    console.log('Skipping deletion of issuer tenants.');
  }

  // // Delete holder tenants
  if (__ENV.SKIP_DELETE_HOLDERS !== 'true') {
    for (const wallet of wallets) {
      const walletId =  getWalletIdByWalletName(bearerToken, wallet.wallet_name);
      const deleteHolderResponse = deleteTenant(bearerToken, walletId);
      check (deleteHolderResponse, {
        "Delete Holder Tenant Response status code is 200": (r) => {
          if (r.status !== 200) {
            console.error(`Unexpected response status while deleting holder tenant ${walletId}: ${r.status}`);
            return false;
          } else {
            console.log(`Deleted holder tenant ${walletId} successfully.`);
            return true;
          }
        }
      });
    }
  }
}
