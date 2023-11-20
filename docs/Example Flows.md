# Example Flow

This document will guide you through an end to end flow:

1. Onboarding an `Issuer`, `Verifier` and a `Holder`.
2. Creating a `Credential Schema`.
3. The `Issuer` creating a `Credential defenition`.
4. Issuing a credential to a `Holder`.
5. The `Verifier` doing a `proof request` against the `Holder's Credential`.
6. Server Sent Events (SSE) 

 >Please be aware that it is assumed at this point that your ecosystem has been [bootstraped](./Bootstrap%20Trust%20Ecosystem.md) with an endorser.

## 1: Onboarding Tenants

When onboarding users, also refered to as tenants, you need to use the `tenant-admin` role.  Below you will find the curl commands used to create an `Issuer`, `Verifier` and a `Holder`. If you are using the [swagger doc](http://localhost:8100/docs) to do the onboarding just use the json in the field marked with `-d` in the curl command. 

The only difference between an `Issuer`, `Verifier` and `Holder` is the roles given to them when created. A tenant can have both the issuer and verifier role and a `Holder` is just a tenant without a role.

>NOTE: See the `x-api-key` used for the tenant creation 

### Onboard Issuer

```bash
curl -X 'POST' \
  'http://localhost:8100/admin/tenants' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant-admin.adminApiKey' \
  -d '{
  "wallet_label": "Demo Issuer",
  "wallet_name": "Faber",
  "roles": [
    "issuer"
  ],
  "group_id": "API demo",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
}'
```
Response
```json
{
  "access_token": "tenant.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXRfaWQiOiI4YTY0YmFhMC0xM2IxLTRlNTgtOWU2Mi05MzNhMDRmMjFlYTQiLCJpYXQiOjE3MDA0NzM3ODZ9.85KxjGW8MGIg-hJsk3PiL3p62zr2LqBP43f9-3IuX6g",
  "wallet_id": "8a64baa0-13b1-4e58-9e62-933a04f21ea4",
  "wallet_label": "Demo Issuer",
  "wallet_name": "Faber",
  "created_at": "2023-11-20T09:49:45.809544Z",
  "updated_at": "2023-11-20T09:49:45.841851Z",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
  "group_id": "API demo"
}
```
### Onboard Verifier

```bash
curl -X 'POST' \
  'http://localhost:8100/admin/tenants' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant-admin.adminApiKey' \
  -d '{
  "wallet_label": "Demo Verifier",
  "wallet_name": "Acme",
  "roles": [
    "verifier"
  ],
  "group_id": "API demo",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
}'
```
Response
```json
{
  "access_token": "tenant.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXRfaWQiOiI5Zjk2YTMxZS0zOGRkLTRiZWMtYjUwZi00YzU4ZTBiYzcwNzYiLCJpYXQiOjE3MDA0NzM4NDd9.pWLI42IG6pZgksMEZaB0KPc5T7kLCzAPlmkcPwnmVyo",
  "wallet_id": "9f96a31e-38dd-4bec-b50f-4c58e0bc7076",
  "wallet_label": "Demo Verifier",
  "wallet_name": "Acme",
  "created_at": "2023-11-20T09:50:46.482996Z",
  "updated_at": "2023-11-20T09:50:46.505080Z",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
  "group_id": "API demo"
}
```
### Onboard Holder
```bash
curl -X 'POST' \
  'http://localhost:8100/admin/tenants' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'x-api-key: tenant-admin.adminApiKey' \
  -d '{
  "wallet_label": "Demo Holder",
  "wallet_name": "Alice",
  "group_id": "API demo",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png"
}'
```
Response
```json
{
  "access_token": "tenant.eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ3YWxsZXRfaWQiOiI3YmIyNGNjOC0yZTU2LTQzMjYtOTAyMC03ODcwYWQ2N2IyNTciLCJpYXQiOjE3MDA0NzM5MDR9.iDwYTPa0JbyNxCAhzsrGu8YykrvsUt643TXIs-uDnGw",
  "wallet_id": "7bb24cc8-2e56-4326-9020-7870ad67b257",
  "wallet_label": "Demo Holder",
  "wallet_name": "Alice",
  "created_at": "2023-11-20T09:51:44.292435Z",
  "updated_at": "2023-11-20T09:51:44.302285Z",
  "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/70/Example.png",
  "group_id": "API demo"
}
```
