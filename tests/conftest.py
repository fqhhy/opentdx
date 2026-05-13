import pytest

from opentdx.client.standardClient import StandardClient
from opentdx.client.extendedClient import ExtendedClient
from opentdx.client.macStandardClient import MacStandardClient
from opentdx.client.macExtendedClient import MacExtendedClient
from opentdx.tdxClient import TdxClient


@pytest.fixture(scope="session")
def tdx():
    client = TdxClient()
    client.q_client().connect().login()
    client.eq_client().connect().login()
    yield client
    if client._quotation_client and client._quotation_client.connected:
        client._quotation_client.disconnect()
    if client._ex_quotation_client and client._ex_quotation_client.connected:
        client._ex_quotation_client.disconnect()


@pytest.fixture(scope="session")
def qc():
    client = StandardClient(True, True)
    client.connect().login()
    yield client
    client.disconnect()


@pytest.fixture(scope="session")
def eqc():
    client = ExtendedClient(True, True)
    client.connect().login()
    yield client
    client.disconnect()


@pytest.fixture(scope="session")
def mqc():
    client = MacStandardClient(True, True)
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture(scope="session")
def meqc():
    client = MacExtendedClient(True, True)
    client.connect()
    yield client
    client.disconnect()


