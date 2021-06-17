import json
import time
import socket

import pytest
import requests
from pytest_bdd import given, scenario, then, when
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def requests_retry_session(
    retries=5,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

FASTAPI_URL = "http://localhost:8000"


@scenario("001_wallet.feature", "Getting a public DID")
def test_GetPublicDid():
    pass


@given("I have an admin API key")
def admin_header():
    admin_headers = {"api-key": "adminApiKey"}
    return admin_headers


@given("I do not have an admin API key")
def admin_header_no_key():
    admin_headers = {}
    return admin_headers


@when("I target the create DID endpoint")
def target_did_enpoint():
    return "/wallets/create-pub-did"


@pytest.mark.asyncio
@then("I am able to generate a public DID")
def test_gen_pub_did():
    header = admin_header()
    endpoint = target_did_enpoint()
    url = FASTAPI_URL + endpoint

    time.sleep(90)
    s = requests.Session()
    s.headers.update(header)
    result = requests_retry_session().get(url)
    result = requests.get(url, headers=header)
    time.sleep(10)
    res_dict = json.loads(result.content)
    assert "did_object" in res_dict
    assert "issuer_verkey" in res_dict
    assert "issuer_endpoint" in res_dict


@then("I am unable to generate a public DID")
def test_gen_pub_did_no_key():
    header = admin_header_no_key()
    endpoint = target_did_enpoint()
    url = FASTAPI_URL + endpoint

    time.sleep(10)
    s = requests.Session()
    s.headers.update(header)
    result = requests_retry_session().get(url)
    time.sleep(5)
    res_dict = json.loads(result.content)
    assert result.status_code == 400
    assert (
        "Bad headers. Either provide an api_key or both wallet_id and tenant_jwt"
        in res_dict["detail"]
    )
    assert "did_object" not in res_dict
    assert "issuer_verkey" not in res_dict
    assert "issuer_endpoint" not in res_dict
