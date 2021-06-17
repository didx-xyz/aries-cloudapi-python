import pytest
from pytest_bdd import scenario, given, when, then
import requests
import aiohttp
import asyncio
import time
import pytest_asyncio


FASTAPI_URL="http://localhost:8000"
# @pytest.fixture 
# def application():
#     helper = LoggingHelper()
#     return helper


# class LoggingHelper:
#     appName = ""
#     appId = None
#     log = ""
#     logStatus = None

@scenario('001_wallet.feature', 'Getting a public DID')
def test_GetPublicDid():
    pass


@given("I have an admin API key")
def admin_header():
    admin_headers = {'req-header': {'api_key': 'adminApiKey'}}
    return admin_header


@when("I target the create DID endpoint")
def target_did_enpoint():
    return "/wallets/create-pub-did"


# @pytest.mark.asyncio
@then("I am able to generate a public DID")
def gen_pub_did():
    header = admin_header()
    endpoint = target_did_enpoint()
    # assert 1 == 2
    url = "http://localhost:8000/wallets/create-pub-did"
    # async with aiohttp.ClientSession() as session:
    #     async with session.get(url, header=header) as resp:
    #         result = await requests.get(FASTAPI_URL, header=admin_header)
        # assert 1 == 2
    # assert "did_objects" in result

#     assert did_object in result
#     assert issuer_ver in result
    # assert 1 == 2

    result = requests.get(url, headers=header)
    time.sleep(10)
    assert "did_object" in result
    # assert "issuer_verkeys" in result.json()
    