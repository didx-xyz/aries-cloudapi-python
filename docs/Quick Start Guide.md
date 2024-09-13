# Quick Start Guide

This guide provides a simple walkthrough for starting, managing, and stopping a
Docker-based project. Please ensure you have the necessary system requirements
and a basic understanding of Docker and Docker Compose.

1. Ensure you have Docker, Docker Compose, Bash, and Mise installed on your
   machine. The project will require about 25GB of free disk space, 16GB of RAM, and
   an average CPU like an modern Intel i5 (min 4 cores).

2. In the root directory of the project, you can start the entire project:

   ```bash
   mise run tilt:up
   ```

3. When you're done, you can stop the project by running:

   ```bash
   mise run tilt:down
   ```

4. If you want to destroy the Kind cluster too:

   ```bash
   mise run tilt:down:destroy
   ```

5. If you want to remove absolutely everything, including the docker cache, for
   a clean slate:

   ```bash
   mise run tilt:down:destroy:all
   ```

## Accessing Services

Once the project is running, you'll have access to several services via Swagger
interfaces. These can be found at the following URLs:

- [CloudAPI-Multitenant-Admin](http://cloudapi.127.0.0.1.nip.io/tenant-admin/docs)
- [CloudAPI-Governance](http://cloudapi.127.0.0.1.nip.io/governance/docs)
- [CloudAPI-Tenant](http://cloudapi.127.0.0.1.nip.io/tenant/docs)
- [CloudAPI-Public](http://cloudapi.127.0.0.1.nip.io/public/docs)
- [ACA-Py Governance Agent Admin](http://governance-agent.cloudapi.127.0.0.1.nip.io)
- [ACA-Py Multitenant Agent Admin](http://multitenant-agent.cloudapi.127.0.0.1.nip.io)
- [Webhooks](http://webhooks.cloudapi.127.0.0.1.nip.io/docs)
- [Trust Registry](http://trust-registry.cloudapi.127.0.0.1.nip.io/docs)

## Customization

Each Docker container's environment parameters can be adjusted via its respective
`.env` file, located in a correspondingly named sub-folder within the
`environments` directory. For example, if you want to change the
`auto-provision` setting for the ACA-Py multitenant instance from `true` to
`false`, adjust the `ACAPY_AUTO_PROVISION` value in
`environments/governance-multitenant/aca-py-agent.default.env`.

Remember to stop and restart the affected containers after making changes.However, be careful when
changing settings like port numbers. These changes will also need to be reflected in the `docker-compose.yaml`
file to ensure that other services are aware of the changes. For instance, if you change `ACAPY_ENDPOINT` or
`ACAPY_WEBHOOK_URL` in an env file of e.g. the multitenant container, you will also want to look to change the
values within the `docker-compose.yaml` to reflect these changes.

The [Common Steps](Common%20Steps.md) document can help you understand how to use the project's infrastructure
once it's up and running.
