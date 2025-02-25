# Bootstrapping the Trust Ecosystem with acapy-cloud

> [!NOTE]
> ⚡ The steps described here are now automated during startup. You can skip this guide under a vanilla setup.

## 1. Prerequisites

Before starting, ensure you have completed the steps in the
[Quick Start Guide](./Quick%20Start%20Guide.md) and have all services running.

## 2. Generate a DID for the Endorser

1. Access the API through the [Governance swagger docs](http://cloudapi.127.0.0.1.nip.io/governance/docs)
2. Authenticate with `governance.`+`APIKEY` role
3. Generate a new DID with a `POST` to the following API endpoint: `/v1/wallet/dids/`
4. An example successful response to generate a DID would look like this:

   ```json
   {
     "did": "LESjYcQUBF2o3kFy5EUqTL",
     "key_type": null,
     "method": null,
     "posture": null,
     "verkey": "BUxNgHYEYm5bsTEpjo9Dkgr5zGA4feeiuiq32HfqyCKg"
   }
   ```

5. Copy the `DID` and `Verkey`

## 3. Anchor New DID to Indy Ledger

1. Go to [Ledger Web Interface](http://localhost:9000/)
2. Select `Register from DID`
3. Paste the `DID` and `Verkey` and select Role `Endorser`
4. Click `Register DID`
5. DID should be successfully written to the Indy Ledger with a response as below

```text
Identity successfully registered:
DID: LESjYcQUBF2o3kFy5EUqTL
Verkey: BUxNgHYEYm5bsTEpjo9Dkgr5zGA4feeiuiq32HfqyCKg
```

## 4. Accept Transaction Author Agreement

1. Connect to ACA-Py [Governance Agent API](http://governance-agent.cloudapi.127.0.0.1.nip.io/api/doc)
2. Authenticate by setting the `x-api-key` header with the API Key of the Governance Agent via Swagger/Postman/Insomnia
3. Get the TAA from the following endpoint `/ledger/taa`. An example response would be like this:

   ```json
   {
     "result": {
       "aml_record": {
         "aml": {
           "at_submission": "The agreement was reviewed by the user and accepted at the time of submission of this transaction.",
           "for_session": "The agreement was reviewed by the user and accepted at some point in the user’s session prior to submission.",
           "on_file": "An authorized person accepted the agreement, and such acceptance is on file with the user’s organization.",
           "product_eula": "The agreement was included in the software product’s terms and conditions as part of a license to the end user.",
           "service_agreement": "The agreement was included in the terms and conditions the user accepted as part of contracting a service.",
           "wallet_agreement": "The agreement was reviewed by the user and this affirmation was persisted in the user’s wallet for use during submission."
         },
         "amlContext": "http://aml-context-descr",
         "version": "1.0"
       },
       "taa_record": {
         "digest": "0be4d87dec17a7901cb8ba8bb4239ee34d4f6e08906f3dad81d1d052dccc078f",
         "ratification_ts": 1597654073,
         "text": "This is a sample Transaction Authors Agreement **(TAA)**, for the VON test Network.\n\nOn public ledger systems this will typically contain legal constraints that must be accepted before any write operations will be permitted.",
         "version": "1.1"
       },
       "taa_required": true,
       "taa_accepted": null
     }
   }
   ```

4. Copy the `text` and `version` from the API response.
5. Accept the TAA by POSTing to the following API endpoint: `/ledger/taa/accept`.

   1. Paste the `text` and `version` from the previous step into the POST body.
   2. Set the `mechanism` to `service_agreement`. A complete POST JSON body example is as follows:

      ```json
      {
        "mechanism": "service_agreement",
        "text": "This is a sample Transaction Authors Agreement **(TAA)**, for the VON test Network.\n\nOn public ledger systems this will typically contain legal constraints that must be accepted before any write operations will be permitted.",
        "version": "1.1"
      }
      ```

      This should yield an empty JSON response with a `200` status code.

## 5. Set Public DID

1. Go to the [Governance interface](http://cloudapi.127.0.0.1.nip.io/governance/docs)
2. Execute the PUT endpoint to set a Public DID: `/v1/wallet/dids/public?did=`
3. Use the DID that you anchored to the ledger in step 3
4. A successful response should look like this. You can also query the Public DID endpoint `/wallet/dids/public` of the
   Governance Agent to confirm that the public DID is now set:

```json
{
  "did": "LESjYcQUBF2o3kFy5EUqTL",
  "key_type": "ed25519",
  "method": "sov",
  "posture": "posted",
  "verkey": "BUxNgHYEYm5bsTEpjo9Dkgr5zGA4feeiuiq32HfqyCKg"
}
```

## 6. Congratulations

1. You have now successfully bootstrapped a Trust Ecosystem with acapy-cloud!
2. You can now write schemas, create credential definitions, manage tenants, and more.

Continue by reading about [Governance as Code](./Governance%20as%20Code.md).
