import http from "k6/http";
import sse from "k6/x/sse"
import { check, sleep } from "k6";
import { Trend, Counter } from "k6/metrics";
// import { sleep } from 'k6';

// let customDuration = new Trend('custom_duration', true);

function logError(response, requestBody) {
  console.error(`Response status: ${response.status}`);
  console.error(`Response body: ${response.body}`);
  if (requestBody) {
    console.error(`Request body: ${requestBody}`);
  }
}

export function createTenant(bearerToken, wallet) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants`;
  const payload = JSON.stringify({
    wallet_label: wallet.wallet_label,
    wallet_name: wallet.wallet_name,
    group_id: "Some Group Id",
    image_url: "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
  });
  const params = {
    headers: {
      "Authorization": `Bearer ${bearerToken}`,
      "Content-Type": "application/json"
    }
  };

  let response = http.post(url, payload, params);
  if (response.status == 200 ) {
    // Request was successful
    // const { wallet_id: walletId, access_token: accessToken } = JSON.parse(response.body);
    // // Store walletId and accessToken for the current VU and iteration
    // const vuKey = `vu_${__VU}`;
    // const iterKey = `iter_${__ITER}`;
    // if (!global[vuKey]) {
    //   global[vuKey] = {};
    // }
    // global[vuKey][iterKey] = {
    //   walletId: walletId,
    //   accessToken: accessToken
    // };
    return response;
  } else {
    // Request failed
    console.warn(`Request failed for VU: ${__VU}, ITER: ${__ITER}`);
    logError(response, payload);
    throw new Error("Failed to create tenant");
  }
}

export function getWalletIdByWalletName(bearerToken, walletName) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants?wallet_name=${walletName}`;
  const params = {
    headers: {
      "Authorization": `Bearer ${bearerToken}`,
      "Content-Type": "application/json"
    }
  };

  let response = http.get(url, params);
  if (response.status >= 200 && response.status < 300) {
    // Request was successful
    const responseData = JSON.parse(response.body);
    // Check if the response is an array and take the first item
    if (Array.isArray(responseData) && responseData.length > 0) {
      const firstItem = responseData[0];
      // Safely access wallet_id without optional chaining
      if (firstItem && firstItem.hasOwnProperty("wallet_id")) {
        return firstItem.wallet_id;
      }
    }
    console.warn(`Wallet not found for wallet_name ${walletName}`);
    console.warn(`Response body: ${response.body}`);
    return null;
  } else {
    logError(response);
    console.warn(`Request failed for wallet_name ${walletName}`);
    return null;
  }
}

export function getTrustRegistryActor(walletName) {
  const url = `${__ENV.CLOUDAPI_URL}/public/v1/trust-registry/actors?actor_name=${walletName}`;
  const params = {
    headers: {
      "Content-Type": 'application/json'
    }
  };

  let response = http.get(url);
  // console.log(`Respone: ${response}`)
  if (response.status == 200) {
    // Request was successful
    // console.log(`Issuer found for actor_name ${walletName}`);
    return response;
  } else {
    logError(response);
    console.warn(`Issuer not on Trust Registry: actor_name ${walletName}`);
    return null;
  }
}

export function getAccessTokenByWalletId(bearerToken, walletId) {
  let start = new Date();
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants/${walletId}/access-token`;

  const params = {
    headers: {
      "Authorization": `Bearer ${bearerToken}`,
    },
  };

  let response = http.get(url, params);

  if (response.status >= 200 && response.status < 300) {
    // Request was successful
    const responseData = JSON.parse(response.body);
    const accessToken = responseData.access_token;
    let end = new Date();
    // customDuration.add(end - start, { step: 'getAccessTokenByWalletId' });
    return accessToken;
  } else {
    // Request failed
    console.error(`Request failed with status ${response.status}`);
    console.error(`Response body: ${response.body}`);
    // throw new Error(`Failed to get access token: ${response.body}`);
    let end = new Date();
    // customDuration.add(end - start, { step: 'getAccessTokenByWalletId' });
    return null;
  }
}

export function deleteTenant(bearerToken, walletId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants/${walletId}`;
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
    },
  };

  try {
    let response = http.del(url, null, params);
    const responseBody = response.body;

    if (response.status === 200) {
      // Request was successful
      if (responseBody === "null") {
        // console.log(`Wallet ${walletId} deleted successfully.`);
      } else {
        console.error(`Failed to delete wallet ${walletId}. Response body: ${responseBody}`);
      }
    } else {
      // Request failed
      console.error(`Request failed with status ${response.status}`);
      console.error(`Response body: ${responseBody}`);
    }

    return response;
  } catch (error) {
    // Handle any errors that occurred during the request
    console.error(`Error deleting tenant: ${error.message}`);
    throw error;
  }
}

export function createIssuerTenant(bearerToken, walletName) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants`;
  const payload = JSON.stringify({
    wallet_label: walletName,
    wallet_name: walletName,
    roles: ["issuer", "verifier"],
    group_id: "Group A",
    image_url: "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
  });
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
      'Content-Type': 'application/json'
    }
  };

  try {
    let response = http.post(url, payload, params);
    if (response.status >= 200 && response.status < 300) {
      return response;
    } else {
      logError(response);
      console.warn(`Request failed for wallet_name ${walletName}`);
      return null;
    }
  } catch (error) {
    console.error(`Error creating issuer tenant: ${error.message}`);
    throw error;
  }
}

export function createInvitation(bearerToken, issuerAccessToken) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/connections/create-invitation`;
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken
    }
  };

  try {
    let response = http.post(url, null, params);
    return response;
  } catch (error) {
    console.error(`Error creating invitation: ${error.message}`);
    throw error;
  }
}

export function acceptInvitation(holderAccessToken, invitationObj) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/connections/accept-invitation`;
  const params = {
    headers: {
      "x-api-key": holderAccessToken,
      'Content-Type': 'application/json'
    }
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = {
      "alias": "holder <> issuer",
      "invitation": invitationObj
    };

    let response = http.post(url, JSON.stringify(requestBody), params);
    return response;
  } catch (error) {
    console.error(`Error accepting invitation: ${error.message}`);
    throw error;
  }
}

export function createCredential(bearerToken, issuerAccessToken, credentialDefinitionId, issuerConnectionId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials`;
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken
    }
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = JSON.stringify({
      "type": "indy",
      "indy_credential_detail": {
        "credential_definition_id": credentialDefinitionId,
        "attributes": {
          "date_of_birth": "1986-09-29",
          "id_number": "8698989898989",
          "country_of_birth": "South Africa",
          "citizen_status": "Citizen",
          "date_of_issue": "2021-09-29",
          "gender": "MALE",
          "surname": "Doe",
          "nationality": "South African",
          "country_of_birth_iso_code": "ZA",
          "names": "John James",
        }
      },
      "save_exchange_record": false,
      "connection_id": issuerConnectionId,
      "protocol_version": "v2"
    });

    // console.log(`credentialDefinitionId: ${credentialDefinitionId}`)
    // console.log(`issuerConnectionId: ${issuerConnectionId}`)

    let response = http.post(url, requestBody, params);
    if (response.status >= 200 && response.status < 300) {
      // Request was successful
      return response;
    } else {
      console.error(`Request failed with status ${response.status}`);
      console.error(`Response body: ${response.body}`);
      return response.body;
    }
  } catch (error) {
    console.error(`Error accepting invitation: ${error.message}`);
    throw error;
  }
}

export function acceptCredential(holderAccessToken, credentialId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials/${credentialId}/request`;
  const params = {
    headers: {
      "x-api-key": holderAccessToken,
      'Content-Type': 'application/json'
    }
  };

  try {
    let response = http.post(url, null, params);
    return response;
  } catch (error) {
    console.error(`Error accepting credential: ${response}`);
    throw error;
  }
}

export function createCredentialDefinition(bearerToken, issuerAccessToken, credDefTag, schemaId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/definitions/credentials`;
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken
    },
    timeout: "120s"
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = JSON.stringify({
      "tag": credDefTag,
      "schema_id": schemaId,
      "support_revocation": true,
      "revocation_registry_size": 100
    });

    let response = http.post(url, requestBody, params);
    console.log(`Response body: ${response.body}`);
    console.log(`Request body: ${requestBody}`);
    return response;
  } catch (error) {
    console.error(`Error creating credential definition: ${error.message}`);
    throw error;
  }
}

export function getCredentialIdByThreadId(holderAccessToken, threadId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials`;
  const params = {
    headers: {
      "x-api-key": holderAccessToken,
      'Content-Type': 'application/json'
    }
  };
  // console.log(`holderAccessToken: ${holderAccessToken}`);
  try {
    let response = http.get(url, params);
    // console.log(`Request headers: ${JSON.stringify(response.request.headers)}`);
    // Parse the response body
    let responseData = JSON.parse(response.body);
    // Iterate over the responseData array
    for (let i = 0; i < responseData.length; i++) {
      let obj = responseData[i];
      // Check if the current object has a matching thread_id
      if (obj.thread_id === threadId) {
        // Return the credential_id if a match is found
        return obj.credential_id;
      }
    }
    // Throw an error if no match is found
    throw new Error(`No match found for threadId: ${threadId}\nResponse body: ${JSON.stringify(responseData, null, 2)}`);
  } catch (error) {
    console.error("Error in getCredentialIdByThreadId:", error);
    throw error; // Re-throw the error to propagate it to the caller
  }
}

export function waitForSSEEvent(holderAccessToken, holderWalletId, threadId) {
  const sseUrl = `${__ENV.CLOUDAPI_URL}/tenant/v1/sse/${holderWalletId}/credentials/thread_id/${threadId}/offer-received`;
  const headers = {
    'x-api-key': holderAccessToken,
  };

  let eventReceived = false;

  const response = sse.open(sseUrl, {
    headers: headers,
    tags: { 'k6_sse_tag': 'credential_offer_received' },
  }, function (client) {
    client.on('event', function (event) {
      // console.log(`event data=${event.data}`);
      const eventData = JSON.parse(event.data);
      if (eventData.topic === 'credentials' && eventData.payload.state === 'offer-received') {
        check(eventData, {
          'Event received': (e) => e.payload.state === 'offer-received',
        });
        eventReceived = true;
        client.close();
      }
    });

    client.on('error', function (e) {
      console.log('An unexpected error occurred: ', e.error());
      client.close();
    });
  });

  check(response, { 'SSE connection established': (r) => r && r.status === 200 });

  // Wait for the event to be received or a maximum duration
  const maxDuration = 10; // 10 seconds
  const checkInterval = 1; // 1 second
  let elapsedTime = 0;

  while (!eventReceived && elapsedTime < maxDuration) {
    console.log(`Waiting for event... Elapsed time: ${elapsedTime}ms`);
    elapsedTime += checkInterval;
    sleep(checkInterval);
  }

  return eventReceived;
}

export function waitForSSEEventConnection(holderAccessToken, holderWalletId, invitationConnectionId) {
  const sseUrl = `${__ENV.CLOUDAPI_URL}/tenant/v1/sse/${holderWalletId}/connections/connection_id/${invitationConnectionId}/completed`;
  const headers = {
    'x-api-key': holderAccessToken,
  };

  let eventReceived = false;

  const response = sse.open(sseUrl, {
    headers: headers,
    tags: { 'k6_sse_tag': 'connection_ready' },
  }, function (client) {
    client.on('event', function (event) {
      // console.log(`event data=${event.data}`);
      const eventData = JSON.parse(event.data);
      if (eventData.topic === 'connections' && eventData.payload.state === 'completed') {
        check(eventData, {
          'Event received': (e) => e.payload.state === 'completed',
        });
        eventReceived = true;
        client.close();
      }
    });

    client.on('error', function (e) {
      console.log('An unexpected error occurred: ', e.error());
      client.close();
    });
  });

  check(response, { 'SSE connection established': (r) => r && r.status === 200 });

  // Create random number between 1 and 3
  // const random = Math.floor(Math.random() * 3) + 1;

  // Wait for the event to be received or a maximum duration
  const maxDuration = 10; // 10 seconds
  const checkInterval = 1; // 1 second
  let elapsedTime = 0;

  while (!eventReceived && elapsedTime < maxDuration) {
    console.log(`Waiting for event... Elapsed time: ${elapsedTime}ms`);
    elapsedTime += checkInterval;
    sleep(checkInterval);
  }
  // if number equals 1, sleep for 1 second
  // if (random === 1) {
  //   console.log("Sleeping for 1 second");
  //   eventReceived = false
  // }
  return eventReceived;
}

export function getCredentialDefinitionId(bearerToken, issuerAccessToken, credDefTag) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/definitions/credentials?schema_version=0.1.0`;
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
      'x-api-key': issuerAccessToken
    }
  };

  let response = http.get(url, params);
  if (response.status >= 200 && response.status < 300) {
    const responseData = JSON.parse(response.body);
    const matchingItem = responseData.find(item => item.tag === credDefTag);

    if (matchingItem) {
      console.log(`Credential definition found for tag ${credDefTag}: ${matchingItem.id}`);
      return matchingItem.id;
    } else {
      console.warn(`Credential definition not found for tag ${credDefTag}`);
      // logError(response);
      return false;
    }
  } else {
    logError(response);
    throw new Error(`Failed to check credential definition existence`);
  }
}

export function sendProofRequest(issuerAccessToken, issuerConnectionId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/send-request`;
  const params = {
    headers: {
      'x-api-key': issuerAccessToken,
      'Content-Type': 'application/json'
    }
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = {
      "type": "indy",
      "indy_proof_request": {
          "requested_attributes": {
              "get_id_number": {"name": "id_number"}
          },
          "requested_predicates": {}
      },
      "save_exchange_record": true,
      "comment": "string",
      "protocol_version": "v2",
      "connection_id": issuerConnectionId
    };

    let response = http.post(url, JSON.stringify(requestBody), params);
    return response;
  } catch (error) {
    console.error(`Error accepting invitation: ${error.message}`);
    throw error;
  }
}

export function waitForSSEEventReceived(holderAccessToken, holderWalletId, threadId) {
  const sseUrl = `${__ENV.CLOUDAPI_URL}/tenant/v1/sse/${holderWalletId}/proofs/thread_id/${threadId}/request-received`;
  const headers = {
    'x-api-key': holderAccessToken,
  };

  let eventReceived = false;

  const response = sse.open(sseUrl, {
    headers: headers,
    // tags: { 'k6_sse_tag': 'proof_request_received' },
  }, function (client) {
    client.on('event', function (event) {
      // console.log(`event data=${event.data}`);
      const eventData = JSON.parse(event.data);
      if (eventData.topic === 'proofs' && eventData.payload.state === 'request-received') {
        check(eventData, {
          'Request received': (e) => e.payload.state === 'request-received',
        });
        eventReceived = true;
        client.close();
      }
    });

    client.on('error', function (e) {
      console.log('An unexpected error occurred: ', e.error());
      client.close();
    });
  });

  check(response, { 'SSE connection established': (r) => r && r.status === 200 });

  // Wait for the event to be received or a maximum duration
  const maxDuration = 10; // 10 seconds
  const checkInterval = 1; // 1 second
  let elapsedTime = 0;

  while (!eventReceived && elapsedTime < maxDuration) {
    console.log(`Waiting for event... Elapsed time: ${elapsedTime}ms`);
    elapsedTime += checkInterval;
    sleep(checkInterval);
  }

  return eventReceived;
}

export function getProofIdByThreadId(holderAccessToken, threadId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/proofs?thread_id=${threadId}`;
  const params = {
    headers: {
      'x-api-key': holderAccessToken,
      'Content-Type': 'application/json'
    }
  };
  // console.log(`holderAccessToken: ${holderAccessToken}`);
  try {
    let response = http.get(url, params);
    // console.log(`Request headers: ${JSON.stringify(response.request.headers)}`);
    // Parse the response body
    let responseData = JSON.parse(response.body);
    // Iterate over the responseData array
    for (let i = 0; i < responseData.length; i++) {
      let obj = responseData[i];
      // Check if the current object has a matching thread_id
      if (obj.thread_id === threadId) {
        // Return the credential_id if a match is found
        return obj.proof_id;
      }
    }
    // Throw an error if no match is found
    throw new Error(`No match found for threadId: ${threadId}\nResponse body: ${JSON.stringify(responseData, null, 2)}`);
  } catch (error) {
    console.error("Error in getProofId:", error);
    throw error; // Re-throw the error to propagate it to the caller
  }
}

export function getProofIdCredentials(holderAccessToken, proofId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/proofs/${proofId}/credentials`;
  const params = {
    headers: {
      'x-api-key': holderAccessToken,
      'Content-Type': 'application/json'
    }
  };
  // console.log(`holderAccessToken: ${holderAccessToken}`);
  try {
    let response = http.get(url, params);
    // console.log(`Request headers: ${JSON.stringify(response.request.headers)}`);
    // Parse the response body
    let responseData = JSON.parse(response.body);
    // Iterate over the responseData array
    for (let i = 0; i < responseData.length; i++) {
      let obj = responseData[i];
      // Check if the current object has a matching thread_id
      let referent = obj.cred_info.referent;
      return referent;
    }
    // Throw an error if no match is found
    throw new Error(`No match found for proofId: ${proofId}\nResponse body: ${JSON.stringify(responseData, null, 2)}`);
  } catch (error) {
    console.error("Error in getProofIdCredentials:", error);
    throw error; // Re-throw the error to propagate it to the caller
  }
}

// tenant/v1/verifier/accept-request
export function acceptProofRequest(holderAccessToken, proofId, referent) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/accept-request`;
  const params = {
    headers: {
      'x-api-key': holderAccessToken,
      'Content-Type': 'application/json'
    }
  };
  try {
    // Construct the request body including the invitation object
    const requestBody = {
      "type": "indy",
      "proof_id": proofId,
      "indy_presentation_spec": {
          "requested_attributes": {
              "get_id_number": {
                  "cred_id": referent,
                  "revealed": true
              }
          },
          "requested_predicates": {},
          "self_attested_attributes": {}
      },
      "diff_presentation_spec": {}
    };

    let response = http.post(url, JSON.stringify(requestBody), params);
    // console.log(`holderAccessToken: ${holderAccessToken}`);
    // console.log(`Response body: ${response.body}`);
    // console.log(`Referent: ${referent}`);
    // console.log(`ProofId: ${proofId}`);
    return response;
  } catch (error) {
    console.error(`Error accepting proof request: ${error.message}`);
    throw error;
  }
}

export function waitForSSEProofDone(issuerAccessToken, issuerWalletId, proofThreadId) {
  const sseUrl = `${__ENV.CLOUDAPI_URL}/tenant/v1/sse/${issuerWalletId}/proofs/thread_id/${proofThreadId}/done`;
  const headers = {
    'x-api-key': issuerAccessToken,
  };

  let eventReceived = false;

  const response = sse.open(sseUrl, {
    headers: headers,
    tags: { 'k6_sse_tag': 'proof_done' },
  }, function (client) {
    client.on('event', function (event) {
      // console.log(`event data=${event.data}`);
      const eventData = JSON.parse(event.data);
      if (eventData.topic === 'proofs' && eventData.payload.state === 'done') {
        check(eventData, {
          'Request received': (e) => e.payload.state === 'done',
        });
        eventReceived = true;
        client.close();
      }
    });

    client.on('error', function (e) {
      console.log('An unexpected error occurred: ', e.error());
      client.close();
    });
  });

  check(response, { 'SSE connection established': (r) => r && r.status === 200 });

  // Wait for the event to be received or a maximum duration
  const maxDuration = 10; // 10 seconds
  const checkInterval = 1; // 1 second
  let elapsedTime = 0;

  while (!eventReceived && elapsedTime < maxDuration) {
    console.log(`Waiting for event... Elapsed time: ${elapsedTime}ms`);
    elapsedTime += checkInterval;
    sleep(checkInterval);
  }

  return eventReceived;
}

export function getProof(issuerAccessToken, issuerConnectionId, proofThreadId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/proofs?thread_id=${proofThreadId}`;
  const params = {
    headers: {
      'x-api-key': issuerAccessToken,
      'Content-Type': 'application/json'
    }
  };
  try {
    // Construct the request body including the invitation object
    const requestBody = {
      "type": "indy",
      "indy_proof_request": {
          "requested_attributes": {
              "get_id_number": {"name": "id_number"}
          },
          "requested_predicates": {}
      },
      "save_exchange_record": true,
      "comment": "string",
      "protocol_version": "v2",
      "connection_id": issuerConnectionId
    };
    let response = http.get(url, params);
    // console.log(`Response body: ${response.body}`);
    // console.log(`IssuerAccessToken: ${issuerAccessToken}`);
    // console.log(`IssuerConnectionId: ${issuerConnectionId}`);
    // console.log(`ProofThreadId: ${proofThreadId}`);
    return response;
  } catch (error) {
    console.error(`Error accepting invitation: ${error.message}`);
    throw error;
  }
}

export function createSchema(bearerToken, schemaName, schemaVersion) {
  const url = `${__ENV.CLOUDAPI_URL}/governance/v1/definitions/schemas`;
  const params = {
    headers: {
      'Authorization': `Bearer ${bearerToken}`,
    },
    timeout: "120s"  };

  try {
    // Construct the request body including the invitation object
    const requestBody = JSON.stringify({
      "name": schemaName,
      "version": schemaVersion,
      "attribute_names": [
        "date_of_birth",
        "id_number",
        "country_of_birth",
        "citizen_status",
        "date_of_issue",
        "gender",
        "surname",
        "nationality",
        "country_of_birth_iso_code",
        "names"
      ]
    });

    let response = http.post(url, requestBody, params);
    console.log(`Response body: ${response.body}`);
    return response;
  } catch (error) {
    console.error(`Error creating schema: ${error.message}`);
    throw error;
  }
}

// {
//   "name": "load_pop",
//   "version": "0.1.0",
//   "attribute_names": [
//     "date_of_birth",
//     "id_number",
//     "country_of_birth",
//     "citizen_status",
//     "date_of_issue",
//     "gender",
//     "surname",
//     "nationality",
//     "country_of_birth_iso_code",
//     "names"
//   ]
// }
