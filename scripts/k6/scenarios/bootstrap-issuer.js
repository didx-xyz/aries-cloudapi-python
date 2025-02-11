/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { bootstrapIssuer } from "../libs/setup.js";
import file from "k6/x/file";

const issuerPrefix = __ENV.ISSUER_PREFIX;
const schemaName = __ENV.SCHEMA_NAME;
const schemaVersion = __ENV.SCHEMA_VERSION;
const numIssuers = __ENV.NUM_ISSUERS;
const holderPrefix = __ENV.HOLDER_PREFIX;
const outputPrefix = `${issuerPrefix}`;

console.log(`Number of Issuers: ${numIssuers}`);

const filepath = `output/${outputPrefix}-create-issuers.json`;
export function setup() {
  file.writeString(filepath, "");
}

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
    file.appendString(filepath, `${JSON.stringify(issuerData)}\n`);
    console.log(`Issuer: ${JSON.stringify(issuerData)}`);
    console.log(`Wallet ID: ${issuerData.walletId}`);
    console.log(
      `Credential Definition ID: ${issuerData.credentialDefinitionId}`
    );
  });

  return issuers;
}
