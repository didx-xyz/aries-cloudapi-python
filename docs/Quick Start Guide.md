# Quick Start Guide

This guide provides a simple walkthrough for starting, managing, and stopping a Docker-based project. Please ensure you have the necessary system requirements and a basic understanding of Docker and Docker Compose.

1. Ensure you have Docker, Docker Compose, Bash, and (optionally) GNU Make installed on your machine. The project will require about 5GB of free disk space, 4GB of RAM, and an average CPU like an Intel i5.

2. In the root directory of the project, you can start the entire project using either GNU Make command:

   ```bash
   make start
   ```

   or Bash command:

   ```bash
   ./manage start # or ./manage up
   ```

3. If you want to start the containers in daemon mode (meaning they'll run in the background), you can use:

   ```bash
   ./manage up-as-daemon
   ```

4. When you're done, you can stop the project by running:

   ```bash
   ./manage down # or ./manage stop
   ```

   or

   ```bash
   make stop
   ```

5. If you want to remove the containers that have been spun up, you can use:

   ```bash
   make stop_n_clean
   ```

## Accessing Services

Once the project is running, you'll have access to several services via Swagger interfaces. These can be found at the following URLs:

- [ACA-Py CloudAPI Admin](http://localhost:8000/docs)
- [ACA-Py Governance Agent Admin](http://localhost:3021)
- [ACA-Py CloudAPI Multitenant](http://localhost:8000/docs)
- [ACA-Py Multitenant Agent Admin](http://localhost:4021)
- [Webhooks](http://localhost:3010/docs)
- [Trust registry](http://localhost:8001/docs)

## Customization

Each Docker container's environment parameters can be adjusted via its respective `.env` file, located in a correspondingly named sub-folder within the `environments` directory. For example, if you want to change the `auto-provision` setting for the ACA-Py multitenant instance from `true` to `false`, adjust the `ACAPY_AUTO_PROVISION` value in `environments/governance-multitenant/aca-py-agent.default.env`.

Remember to stop and restart the affected containers after making changes. However, be careful when changing settings like port numbers. These changes will also need to be reflected in the `docker-compose.yaml` file to ensure that other services are aware of the changes. For instance, if you change `ACAPY_ENDPOINT` or `ACAPY_WEBHOOK_URL` in an env file of e.g. the multitenant container, you will also want to look to change the values withing the `docker-compose.yaml` to reflect these changes.

The `workflows.md` and `commonSteps.md` documents can help you understand how to use the project's infrastructure once it's up and running.
