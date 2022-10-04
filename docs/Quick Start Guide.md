### Quickstart

Assuming you have all necessary requirements installed you can start up the entire project using either GNU Make:

```bash
make start
```

or bash

```bash
./manage start # or ./manage up
```

in the root of the project.


If you want to start the containers in daemon mode you can use
```bash
./manage up-as-daemon
```

You can stop the the project by running

```bash
./manage down # /.manage stop
```

or

```bash
make stop
```

You can rid yourself of the spun-up containers by using

```bash
make stop_n_clean
```

### System Requirements

A machine with:

- docker
- docker-compose
- Bash
- GNU Make (optional)

You probably want at least 5GB of free disk space, 4GB of RAM and an average CPU like an Intel i5.

### Components and tweaking

The standard setup spins up the entire infrastructure required with the following containers having Swagger interfaces:

- [Aca-Py CloudAPI Admin](http://localhost:8000/docs)
- [Aca-Py Governance Agent Admin](http://localhost:3021)
- [Aca-Py CloudAPI Multitenant](http://localhost:8000/docs)
- [Aca-Py Multitenant Agent Admin](http://localhost:4021)
- [Webhooks](http://localhost:3010/docs)
- [Trust registry](http://localhost:8001/docs)

In order to change specific variables and environment parameters for each container internally you likely want to do that in the respective `.env` files. Those are located in sub-folders named correspondingly to the containers within the `environments` folder. For example,
if you wanted to set `auto-provision` for the aca-py multitenant instance form its default value `true` to `false` you can do so by changing `ACAPY_AUTO_PROVISION` to `false` within `environments/governance-multitenant/aca-py-agent.default.env`. Corollary, you can do so for other vars and other containers. Stop the container(s) accordingly and start them back up using docker-compose.

However, a word of caution, watch out when changing things like ports. Here, you will also want to change port mappings within the `docker-compose.yaml` accordingly. For instance, if you change `ACAPY_ENDPOINT` or `ACAPY_WEBHOOK_URL` in an env file of e.g. the multitenant container, you will also want to look to change the values withing the `docker-compose.yaml` to reflect these changes. That means ensure that other containers relying on the service you change params for are aware of these changes.

The `workflows.md` and `commonSteps.md` documents provide a good overview on how to get started with using the infrastructure once it is spun up.
