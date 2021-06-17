import json
import time
import socket

import pytest
import requests
from pytest_bdd import given, scenario, then, when

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

FASTAPI_URL = "http://127.0.0.1:8000"


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

    time.sleep(10)
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
    result = requests.get(url, headers=header)
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
