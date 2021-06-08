import docker
import pytest

import routers.governance
from core import wallet, agent_factory, delegates


def test_foo():
    pass


@pytest.mark.asyncio
async def test_create_public_did():
    setup_env()

    delegates.ledger_url = "https://selfserve.sovrin.org/nym"
    result = await wallet.create_public_did()
    print(result)


def setup_env():
    client = docker.from_env()
    containers_list = client.containers.list()
    print(containers_list)

    container = next(iter(c for c in containers_list if 'aries-cloudapi-python_yoma-ga-agent:latest' in c.image.tags), None)

    if container:
        network = next(iter(container.attrs['NetworkSettings']['Networks'].values()), None)
        ip_address=network['IPAddress']
        agent_factory.admin_url = 'http://'+ip_address
    else:
        agent_factory.admin_url = 'http://localhost'
    print(f'admin url  = {agent_factory.admin_url}')
    agent_factory.admin_port = '3021'
    agent_factory.admin_api_key = 'adminApiKey'
    agent_factory.is_multitenant = False
