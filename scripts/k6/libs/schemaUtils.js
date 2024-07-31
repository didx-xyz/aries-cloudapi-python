// schemaUtils.js

import { createSchema, getSchema } from "./functions.js";

export function createSchemaIfNotExists(bearerToken, schemaName, schemaVersion) {
  const schemaExists = checkSchemaExists(bearerToken, schemaName, schemaVersion);
  if (schemaExists) {
    console.log(`Schema: ${schemaName} version: ${schemaVersion} already exists`);
    return getSchemaId(bearerToken, schemaName, schemaVersion);
  }
    console.log(`Schema: ${schemaName} version: ${schemaVersion} does not exist - creating...`);
    const createSchemaResponse = createSchema(bearerToken, schemaName, schemaVersion);
    if (createSchemaResponse.status === 200) {
      // Schema created successfully
      const schemaData = JSON.parse(createSchemaResponse.body);
      return schemaData.id;
    }
      // Schema creation failed
      console.error(`Failed to create schema ${schemaName} v${schemaVersion}`);
      throw new Error(`Failed to create schema ${schemaName} v${schemaVersion}`);
}

function checkSchemaExists(bearerToken, schemaName, schemaVersion) {
  const getSchemaResponse = getSchema(bearerToken, schemaName, schemaVersion);
  if (getSchemaResponse.status === 200 && getSchemaResponse.body !== "[]") {
    // Schema exists
    return true;
  }
    // Schema does not exist
    return false;
}

function getSchemaId(bearerToken, schemaName, schemaVersion) {
  const getSchemaResponse = getSchema(bearerToken, schemaName, schemaVersion);
  if (getSchemaResponse.status === 200 && getSchemaResponse.body !== "[]") {
    // Schema exists
    const schemaData = JSON.parse(getSchemaResponse.body);
    if (schemaData.length > 0) {
      const schemaId = schemaData[0].id;
      return schemaId;
    }
      console.error("Schema data array is empty");
      return null;
  }
    // Schema does not exist
    console.error("Schema does not exist or request failed");
    return null;
}
