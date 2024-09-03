/* global __ENV, __ITER, __VU */
/* eslint-disable no-undefined, no-console, camelcase */

import { check } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Trend } from "k6/metrics";
import file from "k6/x/file";
import { getBearerToken } from "../libs/auth.js";
import { bootstrapIssuer } from "../libs/setup.js";

const vus = Number.parseInt(__ENV.VUS, 1);
const iterations = Number.parseInt(__ENV.ITERATIONS, 1);
const issuerPrefix = __ENV.ISSUER_PREFIX;
const schemaName = __ENV.SCHEMA_NAME;
const schemaVersion = __ENV.SCHEMA_VERSION;

export default function () {
  const walletName = issuerPrefix;
  const credDefTag = walletName;
  const issuers = bootstrapIssuer(walletName, credDefTag, schemaName, schemaVersion);
  issuers.forEach((issuerData) => {
    console.log(`Wallet ID: ${issuerData.walletId}`);
    console.log(`Credential Definition ID: ${issuerData.credentialDefinitionId}`);
  });
  return issuers;
}
