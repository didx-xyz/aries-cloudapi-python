/* global __ENV, __ITER, __VU */
/* eslint no-undef: "error" */
/* eslint no-console: ["error", { allow: ["warn", "error"] }] */

import http from "k6/http";

export function getBearerToken() {
  const url = `${__ENV.CLOUDAPI_URL}/${__ENV.OAUTH_ENDPOINT}`;
  const clientId = __ENV.CLIENT_ID;
  const clientSecret = __ENV.CLIENT_SECRET;
  const requestBody = `grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}`;

  let response = http.post(url, requestBody, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  if (response.status === 200) {
    let responseData = JSON.parse(response.body);
    let bearerToken = responseData.access_token;
    return bearerToken;
  } else {
    console.error("Error:", response.status_text);
    console.error("Response body:", response.body);
    console.error("Error description:", response.json().error_description);
    throw new Error("Failed to obtain bearer token");
  }
}

export function getGovernanceBearerToken() {
  const url = `${__ENV.CLOUDAPI_URL}/${__ENV.GOVERNANCE_OAUTH_ENDPOINT}`;
  const clientId = __ENV.GOVERNANCE_CLIENT_ID;
  const clientSecret = __ENV.GOVERNANCE_CLIENT_SECRET;
  const requestBody = `grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}`;

  let response = http.post(url, requestBody, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  if (response.status === 200) {
    let responseData = JSON.parse(response.body);
    let bearerToken = responseData.access_token;
    return bearerToken;
  } else {
    console.error("Error:", response.status_text);
    console.error("Response body:", response.body);
    console.error("Error description:", response.json().error_description);
    throw new Error("Failed to obtain bearer token");
  }
}
