## 2: Create Schema
Only the `Governance` role can create Schemas.

>NOTE: See the `x-api-key` used to create schemas
```bash
curl -X 'POST' \
  'http://localhost:8100/generic/definitions/schemas' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: governance.adminApiKey' \
  -d '{
  "name": "Person",
  "version": "0.1.0",
  "attribute_names": [
    "Name","Surname","Age"
  ]
}'
```
Response
```json
{
  "id": "QpSW24YVf61A3sAWxArfF6:2:Person:0.1.0",
  "name": "Person",
  "version": "0.1.0",
  "attribute_names": [
    "Surname",
    "Age",
    "Name"
  ]
}
```
