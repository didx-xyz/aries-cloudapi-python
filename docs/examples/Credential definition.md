## 3: Create Credential Definition
Once a schema has been created by the governance agent, the `Issuer` can create a `credential definition`. He will use the credential definition as his unique reference to the schema.  
```bash 
curl -X 'POST' \
  'http://localhost:8100/generic/definitions/credentials' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant.<Issuer token>' \
  -d '{
  "tag": "Demo Person",
  "schema_id": "FS9J6WZ6KVxwy5eGH32CgM:2:Person:0.1.0",
  "support_revocation": false
}'
```
Response
```json
{
  "id": "2hPti9M3aQqsRCy8N6jrDB:3:CL:10:Demo Person",
  "tag": "Demo Person",
  "schema_id": "QpSW24YVf61A3sAWxArfF6:2:Person:0.1.0"
}
```
