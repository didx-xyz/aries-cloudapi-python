import { check } from 'k6';
import { getBearerToken, getGovernanceBearerToken } from './auth.js';
import {
  createCredentialDefinition,
  getCredentialDefinitionId,
} from "./functions.js";
import { createIssuerIfNotExists } from "../libs/issuerUtils.js";
import { createSchemaIfNotExists } from "../libs/schemaUtils.js";

export function bootstrapIssuer(walletName, credDefTag, schemaName, schemaVersion) {
  const bearerToken = getBearerToken();
  const governanceBearerToken = getGovernanceBearerToken();
  const issuers = [];
  const hack = `${walletName}_0`

  const issuerData = createIssuerIfNotExists(bearerToken, hack);
  check(issuerData, {
    "Issuer data retrieved successfully": (data) => data !== null && data !== undefined,
  });

  if (!issuerData) {
    console.error(`Failed to create or retrieve issuer for ${walletName}_0`);
    return issuers;
  }

  const { issuerWalletId, issuerAccessToken } = issuerData;
  const credentialDefinitionId = getCredentialDefinitionId(bearerToken, issuerAccessToken, credDefTag);

  if (credentialDefinitionId) {
    console.log(`Credential definition already exists for issuer ${walletName}_0 - Skipping creation`);
    issuers.push({
      walletId: issuerWalletId,
      accessToken: issuerAccessToken,
      credentialDefinitionId,
    });
  } else {
    console.warn(`Failed to get credential definition ID for issuer ${walletName}_0`);

    const schemaId = createSchemaIfNotExists(governanceBearerToken, schemaName, schemaVersion);
    check(schemaId, {
      "Schema ID is not null": (id) => id !== null && id !== undefined,
    });

    const createCredentialDefinitionResponse = createCredentialDefinition(
      bearerToken,
      issuerAccessToken,
      credDefTag,
      schemaId,
    );

    check(createCredentialDefinitionResponse, {
      "Credential definition created successfully": (r) => r.status === 200,
    });

    if (createCredentialDefinitionResponse.status === 200) {
      const { id: credentialDefinitionId } = JSON.parse(createCredentialDefinitionResponse.body);
      console.log(`Credential definition created successfully for issuer ${walletName}_0`);
      issuers.push({
        walletId: issuerWalletId,
        accessToken: issuerAccessToken,
        credentialDefinitionId: credentialDefinitionId,
      });
    } else {
      console.error(`Failed to create credential definition for issuer ${walletName}_0`);
    }
  }

  return issuers;
}