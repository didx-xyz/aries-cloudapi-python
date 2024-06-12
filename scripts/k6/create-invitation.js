import { check } from 'k6';
import { SharedArray } from 'k6/data';
import { getBearerToken } from './auth.js';
import { Trend, Counter } from 'k6/metrics';
import file from 'k6/x/file';
// import exec from 'k6/execution';
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
    'specific_function_reqs{my_custom_tag:specific_function}': ['count>=0'],
    'specific_function_reqs{scenario:default}': ['count>=0'],
    // 'custom_duration{step:getAccessTokenByWalletId}': ['avg>=0'],
  },
};

const specificFunctionReqs = new Counter('specific_function_reqs');
const mainIterationDuration = new Trend('main_iteration_duration');

const inputFilepath = 'output/create-holders.json';
const data = open(inputFilepath, 'r');
const outputFilepath = 'output/create-invitation.json';

// // Seed data: Generating a list of options.iterations unique wallet names
// const wallets = new SharedArray('wallets', function() {
//   const walletsArray = [];
//   for (let i = 0; i < options.iterations; i++) {
//     walletsArray.push({
//       wallet_label: `xxkk6 holder ${i}`,
//       wallet_name: `xxkk6_wallet_${i}`
//     });
//   }
//   return walletsArray;
// });

const numIssuers = 1;
let issuers = [];

export function setup() {
  const bearerToken = getBearerToken();
  const issuers = [];

  const holders = data.trim().split('\n').map(JSON.parse);

  // Example usage of the loaded data
  holders.forEach((holderData) => {
    console.log(`Processing wallet ID: ${holderData.wallet_id}`);
    // Your test logic here, e.g., make HTTP requests using the holderData
  });

  file.writeString(outputFilepath, '');

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

  return { bearerToken, issuers, holders };
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

  const holders = data.holders;
  const wallet = holders[walletIndex];


  const issuerIndex = __ITER % numIssuers;
  const issuer = issuers[issuerIndex];

  // const holderWalletId = getWalletIdByWalletName(bearerToken, wallet.wallet_name);
  // check(holderWalletId, {
  //   "Holder wallet ID is not null": (r) => r !== null
  // });

  // const holderAccessToken = getAccessTokenByWalletId(bearerToken, holderWalletId);
  // check(holderAccessToken, {
  //   "Holder access token is not null": (r) => r !== null
  // });

  const createInvitationResponse = createInvitation(bearerToken, issuer.accessToken);
  check(createInvitationResponse, {
    "Invitation created successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response status while create invitation: ${r.status}`);
      }
      return true;
    }
  });
  const { invitation: invitationObj, connection_id: issuerConnectionId } = JSON.parse(createInvitationResponse.body);

  const acceptInvitationResponse = acceptInvitation(wallet.access_token, invitationObj);
  check(acceptInvitationResponse, {
    "Invitation accepted successfully": (r) => {
      if (r.status !== 200) {
        throw new Error(`Unexpected response while accepting invitation: ${r.response}`);
      }
      return true;
    }
  });

  const { connection_id: holderInvitationConnectionId } = JSON.parse(acceptInvitationResponse.body);

  const waitForSSEEventConnectionResponse = waitForSSEEventConnection(wallet.access_token, wallet.wallet_id, holderInvitationConnectionId);
  check(waitForSSEEventConnectionResponse, {
    'SSE Event received successfully: connection-ready': (r) => {
      if (!r) {
        throw new Error('SSE event was not received successfully');
      }
      return true;
    },
  });

  specificFunctionReqs.add(1, { my_custom_tag: 'specific_function' });

  // holders.push({
  //   wallet_label: wallet.wallet_label,
  //   wallet_name: wallet.wallet_name,
  //   wallet_id: wallet.wallet_id,
  //   access_token: wallet.access_token,
  //   connection_id: holderInvitationConnectionId,
  //   issuer_connection_id: issuerConnectionId,
  // });
  // console.log('Holder added to array:', holders[holders.length - 1]);

  // // Write holders array to file
  // const filepath = 'holders.json';
  // const output = JSON.stringify(holders);
  // file.writeString(filepath, output);

  // console.log('Writing xxxxxxxxxxxx:', output);
  // Store the holder data in exec.vu.tags as a JSON string
  const holderData = JSON.stringify({
    wallet_label: wallet.wallet_label,
    wallet_name: wallet.wallet_name,
    wallet_id: wallet.wallet_id,
    access_token: wallet.access_token,
    connection_id: holderInvitationConnectionId,
    issuer_connection_id: issuerConnectionId,
  });
  file.appendString(outputFilepath, holderData + '\n');

  const end = Date.now();
  const duration = end - start;
  console.log(`Duration for iteration ${__ITER}: ${duration} ms`);
  mainIterationDuration.add(duration);
}

export function teardown(data) {
  const bearerToken = data.bearerToken;
  const issuers = data.issuers;
  const holders = data.holders;

  // console.log('I CAN STILL READ:', holders[holders.length - 1]);

  // const filepath = 'holders.json';

  // // Convert the holders array to a JSON string
  // const output = JSON.stringify(holders);

  // Write the JSON string to the file
  // try {
  //   file.writeString(filepath, output);
  //   console.log('Holders array written to file:', filepath);
  // } catch (error) {
  //   console.error('Error writing holders array to file:', error);
  // }

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
    for (const wallet of holders) {
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
  } else {
    console.log('Skipping deletion of holder tenants.');
  }
}
