import http from 'k6/http';

export function getBearerToken() {
  const url = `https://${__ENV.cloudapi_url}/${__ENV.oauth_endpoint}`;
  const clientId = __ENV.client_id;
  const clientSecret = __ENV.client_secret;
  const requestBody = `grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}`;

  let response = http.post(url, requestBody, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    }
  });

  if (response.status === 200) {
    let responseData = JSON.parse(response.body);
    let bearerToken = responseData.access_token;
    console.log("Extracted bearer token:", bearerToken);
    return bearerToken;
  } else {
    console.error("Error:", response.status_text);
    console.error("Error description:", response.json().error_description);
    throw new Error("Failed to obtain bearer token");
  }
}