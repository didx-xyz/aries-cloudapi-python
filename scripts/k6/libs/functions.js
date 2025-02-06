/* global __ENV, __ITER, __VU, console */
/* eslint-disable no-undefined, no-console, camelcase */

import { check, sleep } from "k6";
import http from "k6/http";
import sse from "k6/x/sse";
// let customDuration = new Trend('custom_duration', true);

// Helper function to generate a unique, zero-based index for even distribution of operations
export function getWalletIndex(vu, iter, iterationsPerVu) {
  return (vu - 1) * iterationsPerVu + iter;
}

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
    image_url:
      "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
  });
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
    },
  };

  const response = http.post(url, payload, params);
  if (response.status === 200) {
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
  }
  // Request failed
  console.warn(`Request failed for VU: ${__VU}, ITER: ${__ITER}`);
  logError(response, payload);
  throw new Error("Failed to create tenant");
}

export function getWalletIdByWalletName(bearerToken, walletName) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants?wallet_name=${walletName}`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
    },
  };

  const response = http.get(url, params);
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
  }
  logError(response);
  console.warn(`Request failed for wallet_name ${walletName}`);
  return null;
}

export function getTrustRegistryActor(walletName) {
  const url = `${__ENV.CLOUDAPI_URL}/public/v1/trust-registry/actors?actor_name=${walletName}`;
  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const response = http.get(url);
  // console.log(`Response: ${response}`)
  if (response.status === 200) {
    // Request was successful
    // console.log(`Issuer found for actor_name ${walletName}`);
    return response;
  }
  logError(response);
  console.warn(`Issuer not on Trust Registry: actor_name ${walletName}`);
  return null;
}

export function getAccessTokenByWalletId(bearerToken, walletId) {
  const start = new Date();
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants/${walletId}/access-token`;

  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
  };

  const response = http.get(url, params);

  if (response.status >= 200 && response.status < 300) {
    // Request was successful
    const responseData = JSON.parse(response.body);
    const accessToken = responseData.access_token;
    const end = new Date();
    // customDuration.add(end - start, { step: 'getAccessTokenByWalletId' });
    return accessToken;
  }
  // Request failed
  console.error(`Request failed with status ${response.status}`);
  console.error(`Response body: ${response.body}`);
  // throw new Error(`Failed to get access token: ${response.body}`);
  const end = new Date();
  // customDuration.add(end - start, { step: 'getAccessTokenByWalletId' });
  return null;
}

export function deleteTenant(bearerToken, walletId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/v1/tenants/${walletId}`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
  };

  try {
    const response = http.del(url, null, params);
    const responseBody = response.body;

    if (response.status === 204 || response.status === 200) {
      // Request was successful
      if (responseBody === null) {
        // console.log(`Wallet ${walletId} deleted successfully.`);
      } else {
        console.error(
          `Failed to delete wallet ${walletId}. Response body: ${responseBody}`
        );
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
    image_url:
      "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
  });
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "Content-Type": "application/json",
    },
  };

  try {
    const response = http.post(url, payload, params);
    if (response.status >= 200 && response.status < 300) {
      return response;
    }
    logError(response);
    console.warn(`Request failed for wallet_name ${walletName}`);
    return null;
  } catch (error) {
    logError(response);
    console.error(`Error creating issuer tenant: ${error.message}`);
    throw error;
  }
}

export function createInvitation(bearerToken, issuerAccessToken) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/connections/create-invitation`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken,
    },
  };

  try {
    const response = http.post(url, null, params);
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
      "Content-Type": "application/json",
    },
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = {
      alias: "holder <> issuer",
      invitation: invitationObj,
    };

    const response = http.post(url, JSON.stringify(requestBody), params);
    return response;
  } catch (error) {
    console.error(`Error accepting invitation: ${error.message}`);
    throw error;
  }
}

export function createCredential(
  bearerToken,
  issuerAccessToken,
  credentialDefinitionId,
  issuerConnectionId
) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken,
    },
  };

  // console.log(`credentialDefinitionId: ${credentialDefinitionId}`);
  // console.log(`Request Body: ${JSON.stringify(params)}`);

  try {
    // Construct the request body including the invitation object
    const requestBody = JSON.stringify({
      type: "indy",
      indy_credential_detail: {
        credential_definition_id: credentialDefinitionId,
        attributes: {
          date_of_birth: "1986-09-29",
          id_number: "8698989898989",
          country_of_birth: "South Africa",
          citizen_status: "Citizen",
          date_of_issue: "2021-09-29",
          gender: "MALE",
          surname: "Doe",
          nationality: "South African",
          country_of_birth_iso_code: "ZA",
          names: "John James",
        },
      },
      save_exchange_record: false,
      connection_id: issuerConnectionId,
    });

    // console.log(`credentialDefinitionId: ${credentialDefinitionId}`)
    // console.log(`issuerConnectionId: ${issuerConnectionId}`)

    const response = http.post(url, requestBody, params);
    if (response.status >= 200 && response.status < 300) {
      return response;
    }
    console.error(`Request failed with status ${response.status}`);
    console.error(`Response body: ${response.body}`);
    return response.body;
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
      "Content-Type": "application/json",
    },
  };

  try {
    const response = http.post(url, null, params);
    return response;
  } catch (error) {
    console.error(`Error accepting credential: ${error.message}`);
    throw error;
  }
}

export function createCredentialDefinition(
  bearerToken,
  issuerAccessToken,
  credDefTag,
  schemaId
) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/definitions/credentials`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken,
    },
    timeout: "120s",
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = JSON.stringify({
      tag: credDefTag,
      schema_id: schemaId,
      support_revocation: true,
      revocation_registry_size: 100,
    });

    const response = http.post(url, requestBody, params);

    if (response.status == 200) {
      return response;
    }
    logError(response);
    console.warn(
      `Failed creating credential definition. Request Body: ${requestBody}`
    );
    return null;
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
      "Content-Type": "application/json",
    },
  };
  // console.log(`holderAccessToken: ${holderAccessToken}`);
  try {
    const response = http.get(url, params);
    // console.log(`Request headers: ${JSON.stringify(response.request.headers)}`);
    // Parse the response body
    const responseData = JSON.parse(response.body);
    // Iterate over the responseData array
    for (let i = 0; i < responseData.length; i++) {
      const obj = responseData[i];
      // Check if the current object has a matching thread_id
      if (obj.thread_id === threadId) {
        // Return the credential_id if a match is found
        return obj.credential_id;
      }
    }
    // Throw an error if no match is found
    throw new Error(
      `No match found for threadId: ${threadId}\nResponse body: ${JSON.stringify(
        responseData,
        null,
        2
      )}`
    );
  } catch (error) {
    console.error("Error in getCredentialIdByThreadId:", error);
    throw error; // Re-throw the error to propagate it to the caller
  }
}

export function getCredentialDefinitionId(
  bearerToken,
  issuerAccessToken,
  credDefTag
) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/definitions/credentials?schema_version=0.1.0`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
      "x-api-key": issuerAccessToken,
    },
  };

  const response = http.get(url, params);
  if (response.status >= 200 && response.status < 300) {
    const responseData = JSON.parse(response.body);
    const matchingItem = responseData.find((item) => item.tag === credDefTag);

    if (matchingItem) {
      console.log(
        `Credential definition found for tag ${credDefTag}: ${matchingItem.id}`
      );
      return matchingItem.id;
    }
    console.warn(`Credential definition not found for tag ${credDefTag}`);
    // logError(response);
    return false;
  }
  logError(response);
  throw new Error("Failed to check credential definition existence");
}

export function sendProofRequest(issuerAccessToken, issuerConnectionId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/send-request`;
  const params = {
    headers: {
      "x-api-key": issuerAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    // Get current epoch time in seconds
    const currentEpochTimeSeconds = Math.floor(Date.now() / 1000);

    // Construct the request body including the invitation object
    const requestBody = {
      type: "indy",
      indy_proof_request: {
        non_revoked: {
          to: currentEpochTimeSeconds, // Current epoch time in seconds
        },
        requested_attributes: {
          get_id_number: { name: "id_number" },
        },
        requested_predicates: {},
      },
      save_exchange_record: true,
      comment: "string",
      connection_id: issuerConnectionId,
    };
    const response = http.post(url, JSON.stringify(requestBody), params);
    return response;
  } catch (error) {
    console.error(`Error accepting invitation: ${error.message}`);
    throw error;
  }
}

export function getProofIdByThreadId(holderAccessToken, threadId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/proofs?thread_id=${threadId}`;
  const params = {
    headers: {
      "x-api-key": holderAccessToken,
      "Content-Type": "application/json",
    },
  };
  // console.log(`holderAccessToken: ${holderAccessToken}`);
  try {
    const response = http.get(url, params);
    // console.log(`Request headers: ${JSON.stringify(response.request.headers)}`);
    // Parse the response body
    const responseData = JSON.parse(response.body);
    // Iterate over the responseData array
    for (let i = 0; i < responseData.length; i++) {
      const obj = responseData[i];
      // Check if the current object has a matching thread_id
      if (obj.thread_id === threadId) {
        // Return the credential_id if a match is found
        // console.log(`Log of the request made: ${JSON.stringify(response.request)}`);
        return obj.proof_id;
      }
    }
    // Throw an error if no match is found
    throw new Error(
      `No match found for threadId: ${threadId}\nResponse body: ${JSON.stringify(
        responseData,
        null,
        2
      )}`
    );
  } catch (error) {
    console.error("Error in getProofId:", error);
    throw error; // Re-throw the error to propagate it to the caller
  }
}

export function getProofIdCredentials(holderAccessToken, proofId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/proofs/${proofId}/credentials`;
  const params = {
    headers: {
      "x-api-key": holderAccessToken,
      "Content-Type": "application/json",
    },
  };
  // console.log(`holderAccessToken: ${holderAccessToken}`);
  try {
    const response = http.get(url, params);
    // console.log(`Request headers: ${JSON.stringify(response.request.headers)}`);
    // Parse the response body
    const responseData = JSON.parse(response.body);
    // Iterate over the responseData array
    for (let i = 0; i < responseData.length; i++) {
      const obj = responseData[i];
      // Check if the current object has a matching thread_id
      const referent = obj.cred_info.referent;
      // TODO: this will always return the first referent - fix this
      return referent;
    }
    // Throw an error if no match is found
    // console.log(`Log of the request made: ${JSON.stringify(response.request)}`);
    throw new Error(
      `No match found for proofId: ${proofId}\nResponse body: ${JSON.stringify(
        responseData,
        null,
        2
      )}`
    );
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
      "x-api-key": holderAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    // Construct the request body including the invitation object
    const requestBody = {
      type: "indy",
      proof_id: proofId,
      indy_presentation_spec: {
        requested_attributes: {
          get_id_number: {
            cred_id: referent,
            revealed: true,
          },
        },
        requested_predicates: {},
        self_attested_attributes: {},
      },
      diff_presentation_spec: {},
    };

    const response = http.post(url, JSON.stringify(requestBody), params);
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

export function getProof(issuerAccessToken, issuerConnectionId, proofThreadId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/verifier/proofs?thread_id=${proofThreadId}`;
  const params = {
    headers: {
      "x-api-key": issuerAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    // Construct the request body including the invitation object
    const requestBody = {
      type: "indy",
      indy_proof_request: {
        requested_attributes: {
          get_id_number: { name: "id_number" },
        },
        requested_predicates: {},
      },
      save_exchange_record: true,
      comment: "string",
      connection_id: issuerConnectionId,
    };
    const response = http.get(url, params);
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

export function getDocs() {
  const url = `${__ENV.CLOUDAPI_URL}/tenant-admin/docs`;
  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };
  try {
    const response = http.get(url, params);
    return response;
  } catch (error) {
    console.error(`Error getting docs: ${error.message}`);
    throw error;
  }
}

export function createSchema(bearerToken, schemaName, schemaVersion) {
  const url = `${__ENV.CLOUDAPI_URL}/governance/v1/definitions/schemas`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
    timeout: "120s",
  };

  try {
    // Construct the request body including the invitation object
    const requestBody = JSON.stringify({
      name: schemaName,
      version: schemaVersion,
      attribute_names: [
        "date_of_birth",
        "id_number",
        "country_of_birth",
        "citizen_status",
        "date_of_issue",
        "gender",
        "surname",
        "nationality",
        "country_of_birth_iso_code",
        "names",
      ],
    });

    const response = http.post(url, requestBody, params);
    // console.log(`Response body: ${response.body}`);
    return response;
  } catch (error) {
    console.error(`Error creating schema: ${error.message}`);
    throw error;
  }
}

export function getSchema(bearerToken, schemaName, schemaVersion) {
  const url = `${__ENV.CLOUDAPI_URL}/governance/v1/definitions/schemas?schema_name=${schemaName}&schema_version=${schemaVersion}`;
  const params = {
    headers: {
      Authorization: `Bearer ${bearerToken}`,
    },
  };

  try {
    const response = http.get(url, params);
    // console.log(`Response XXX body: ${response.body}`);
    return response;
  } catch (error) {
    console.error(`Error getting schema: ${error.message}`);
    throw error;
  }
}

export function revokeCredential(issuerAccessToken, credentialExchangeId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials/revoke`;
  const params = {
    headers: {
      "x-api-key": issuerAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    const requestBody = {
      credential_exchange_id: credentialExchangeId,
    };
    const response = http.post(url, JSON.stringify(requestBody), params);

    if (response.status !== 200) {
      console.error(`Unexpected status code: ${response.status}`);
      console.error(`Response body: ${response.body}`);
    }

    return response;
  } catch (error) {
    console.error(`Error revoking credential: ${error.message}`);
    throw error;
  }
}

export function revokeCredentialAutoPublish(
  issuerAccessToken,
  credentialExchangeId
) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials/revoke`;
  const params = {
    headers: {
      "x-api-key": issuerAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    const requestBody = {
      credential_exchange_id: credentialExchangeId,
      auto_publish_on_ledger: true,
    };
    const response = http.post(url, JSON.stringify(requestBody), params);

    if (response.status !== 200) {
      console.error(`Unexpected status code: ${response.status}`);
      console.error(`Response body: ${response.body}`);
    }

    return response;
  } catch (error) {
    console.error(`Error revoking credential: ${error.message}`);
    throw error;
  }
}

export function publishRevocation(issuerAccessToken) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials/publish-revocations`;
  const params = {
    headers: {
      "x-api-key": issuerAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    const requestBody = {
      revocation_registry_credential_map: {},
    };
    const response = http.post(url, JSON.stringify(requestBody), params);

    if (response.status !== 200) {
      console.error(`Unexpected status code: ${response.status}`);
      console.error(`Response body: ${response.body}`);
    }

    return response;
  } catch (error) {
    console.error(`Error revoking credential: ${error.message}`);
    throw error;
  }
}

export function checkRevoked(issuerAccessToken, credentialExchangeId) {
  const url = `${__ENV.CLOUDAPI_URL}/tenant/v1/issuer/credentials/revocation/record?credential_exchange_id=${credentialExchangeId}`;
  const params = {
    headers: {
      "x-api-key": issuerAccessToken,
      "Content-Type": "application/json",
    },
  };
  try {
    const response = http.get(url, params);
    return response;
  } catch (error) {
    console.error(`Error checking if credential is revoked: ${error.message}`);
    throw error;
  }
}

// TODO: refactor the maxDuration logic. It's not being used properly. Actually relies on server-side timeout.

export function genericWaitForSSEEvent(config) {
  const {
      accessToken,
      walletId,
      threadId,
      eventType,
      sseUrlPath,
      topic,
      expectedState,
      lookBack = 5,
      maxDuration, // this does nothing...
      maxRetries = 3,
      retryDelay = 1,
  } = config;

  const sseUrl = `${__ENV.CLOUDAPI_URL}/tenant/v1/sse/${walletId}/${sseUrlPath}/${threadId}/${eventType}?look_back=${lookBack}`;
  const headers = {
      "x-api-key": accessToken,
  };
  let retryCount = 0;

  function connectSSE() {
      return new Promise((resolve, reject) => {
          let timeoutId;

          // Create a timeout Promise
          const timeoutPromise = new Promise((_, timeoutReject) => {
              timeoutId = setTimeout(() => {
                  console.error(`Max duration ${maxDuration}s exceeded for this attempt`);
                  timeoutReject(new Error("TIMEOUT"));
              }, maxDuration * 1000);
          });

          const ssePromise = new Promise((sseResolve, sseReject) => {
              const response = sse.open(
                  sseUrl,
                  {
                      headers,
                      tags: config.sseTag ? { k6_sse_tag: config.sseTag } : undefined,
                  },
                  (client) => {
                      client.on("event", (event) => {
                          if (!event.data || event.data.trim() === "") {
                              console.warn("Received empty event data (ping)");
                              return; // Continue waiting
                          }
                          let eventData;
                          try {
                              eventData = JSON.parse(event.data);
                          } catch (error) {
                              console.warn(`Error parsing event data: ${error.message}`);
                              client.close();
                              clearTimeout(timeoutId);
                              sseReject(new Error("Failed to parse event data"));
                              return;
                          }
                          if (
                              typeof eventData === "object" &&
                              eventData.topic === topic &&
                              eventData.payload &&
                              eventData.payload.state === expectedState
                          ) {
                              check(eventData, {
                                  "Event received": (e) => e.payload.state === expectedState,
                              });
                              // console.log(`VU ${__VU}: Iteration ${__ITER}: Received expected event: ${JSON.stringify(eventData)}`);
                              client.close();
                              clearTimeout(timeoutId);
                              sseResolve(true);
                          } else {
                              console.error(`Received unexpected event: ${JSON.stringify(eventData)}`);
                              client.close();
                              clearTimeout(timeoutId);
                              sseResolve(false);
                          }
                      });

                      client.on("error", (e) => {
                          console.warn("SSE connection error: ", e.error());
                          client.close();
                          clearTimeout(timeoutId);
                          sseReject(new Error("SSE connection error"));
                      });

                      client.on("end", () => {
                          console.log("SSE connection closed");
                          clearTimeout(timeoutId);
                          sseReject(new Error("SSE connection closed unexpectedly"));
                      });
                  }
              );

              if (!response || response.status !== 200) {
                  clearTimeout(timeoutId);
                  sseReject(new Error("Failed to establish initial SSE connection"));
                  return;
              }
              check(response, {
                  "SSE connection established": (r) => r && r.status === 200,
              });
          });

          // Race between the SSE connection and the timeout
          Promise.race([ssePromise, timeoutPromise])
              .then(resolve)
              .catch(error => {
                  if (error.message === "TIMEOUT") {
                      resolve(false);  // Timeout case
                  } else {
                      reject(error);  // Other errors
                  }
              });
      });
  }

  async function attemptConnection() {
      while (retryCount <= maxRetries) {
          try {
              if (retryCount > 0) {
                  console.warn(`VU ${__VU}: Iteration ${__ITER}: Attempting SSE reconnection (attempt ${retryCount}/${maxRetries})`);
              }
              const result = await connectSSE();
              if (!result) {
                  console.error("SSE connection attempt failed");
                  return false;
              }
              return true;
          } catch (error) {
              console.warn(`Connection attempt failed: ${error.message}`);
              if (retryCount < maxRetries) {
                  retryCount++;
                  console.log(`Retrying in ${retryDelay} seconds...`);
                  sleep(retryDelay);
              } else {
                  console.error("Max retries exceeded without successful connection");
                  return false;
              }
          }
      }
      return false;
  }

  return attemptConnection();
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
