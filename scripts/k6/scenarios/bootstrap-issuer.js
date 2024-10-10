/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { bootstrapIssuer } from "../libs/setup.js";

const issuerPrefix = __ENV.ISSUER_PREFIX;
const schemaName = __ENV.SCHEMA_NAME;
const schemaVersion = __ENV.SCHEMA_VERSION;
const numIssuers = __ENV.NUM_ISSUERS;

console.log(`Number of Issuers: ${numIssuers}`);

export default function () {
  const walletName = issuerPrefix;
  const credDefTag = walletName;
  const issuers = bootstrapIssuer(
    numIssuers,
    issuerPrefix,
    credDefTag,
    schemaName,
    schemaVersion
  );
  issuers.forEach((issuerData) => {
    console.log(`Wallet ID: ${issuerData.walletId}`);
    console.log(
      `Credential Definition ID: ${issuerData.credentialDefinitionId}`
    );
  });
  return issuers;
}
