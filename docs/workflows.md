## Workflows

### First Steps

After spinning up the containers following the `README` or `intro.md` you are ready ot rumble. Navigating to the [swagger UI](http://localhost:8000/docs/) provides a good overview of the intended functionalities.

You see that tehre are `generic` endpoints for common actions, wallet specific actions and admin actions. On top of that, you find th trust registry and webhooks being exposed. These are the intended ways of client interactions with these two services.

NOTE: Regardless of the multitude of containers and mechanisms running, [the CloudAPI](http://localhost:8000) and its [SwaggerUI](http://localhost:8000/docs) are the main interaction point intended between clients and the stack. This should be the only endpoint clients should (have to) interact with. There is no need (and no intention to allow that) for client to directly interact with the webhooks or trustregistry container. For a production deployment or a close-to-proudction/smoke-testing deployment, you are well adviced to only expose this endpoint to clients and leave all other endpoints unexposed to the outside world.

#### Trust registry

As a client you can retrieve the trust registry (and NOT alter it). That is intentional and all a consumer/client should and is able to do. Altering the trust registry is baked into admin actions and only possible with admin role.

#### Webhooks

A client can subscribe to the webhooks via the CloudAPI (as opposed to directly via the webhooks container). This requires only targeting the `/webhooks` endpoint and optionally targeting the `/webhooks/{topic}` sub-route by suffixing a topic. Using the auth mechanism (see section below), the app automatically extracts the required info about the wallet (i.e the wallet id and JWT) and retrieves only the associated webhooks with a particular wallet. Failing to authenticate will return a 403 HTTP Error.

### Authentication

Authentication is handled by the CloudAPI and, fom a client perspective, kept simple and convenient. Either, via the Swagger UI auth (padlock button in UI) or via the HEADER data of your client specifying an `x-api-key`. Regardless of whether ou use the UI or another client, the `x-api-key` value consists of two parts, separated by a dot:

`{role}.{key/password}`

So, your header has the format `'x-api-key: {role}.{key/password}` which yields, for example, `'x-api-key: yoma.adminApiKey'`

The first part `role` specifies the role on the surface and targets the correct endpoints under the hood and authentication mechanisms under the hood. The CloudAPI knows how to interpret the roles and will produce the correct target URLs for eg aca-py (`member` targets the multitenant agent) with the correct header expected by aca-py agent. For instance, `member` results in a `Bearer {TOKEN}` header against the multitenant agent whereas `member-admin` as role results in an `x-api-key` header for the multitenant agent (hence targeting the admin interface of the same multitennat agent). You may have noticed now that this mechanism also chooses which aca-py instance to target without having to know or specify the URL the agent resides under.

Currently there are five options for `role`:

- yoma
- ecosystem
- ecosystem-admin
- member
- member-admin

the `yoma` and `-admin` suffixed roles are admin roles. The rest are non-admin roles meaning non-admin roles have no exposure to the aca-py admin tasks nor any documented endpoints prefixed `admin:` in the CloudAPI.

For admin roles pass the admin password as the second part of `{role}.{key/password}`. For member/ecosystem (non-admin roles) pass the wallets JWT as the second part of `{role}.{key/password}`.

### Creating schemas

Using the admin role(s) you can create and register schemas. Successful schema creating will automatically write it to the ledger.

The ledger is also a useful place to look at what schemas you have at your disposal. In fact, this should be the preferred way because schemas can exist on the ledger but have been invalidated on the trust registry. This will be checked by the CloudAPI and only valid schemas are allowed for use.

### User management/Creating wallets

Using the admin role(s) you can create wallets for tenant or eco-system partners. These are all sub wallets. Successful creation return the wallet creation response including the wallet id and JWT for authentication.

### Using the swagger UI

The Swagger UI is documented. It shows you endpoints, expected parameters and what example requests and responses look like. At the bottom of the UI you can also find a list of all types used that includes definition and example values.

### Following logs

It can be handy to follow the logs of a specific container. A convenient way to do so is using:

```bash
docker logs --follow $(docker ps -f name="YOUR_CONTAINER_NAME" | awk 'FNR == 2 {print $1}')
```

and replacing `YOUR_CONTAINER_NAME` with the name of the container you want to follow (eg yoma-webhooks-web). You can find the container name in the docker-compose.yaml.
