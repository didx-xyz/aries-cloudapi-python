import pytest
import mockito
# Unused imports contain fixtures
from app.webhooks import Webhooks

# In pytest, conftest.py is a special file used to share fixtures, hooks, and other configurations
# among multiple test files. It's automatically discovered by pytest when tests are run, and the
# fixtures and hooks defined within it can be used in any test file within the same directory or subdirectories.

# Pytest fixtures are reusable components that can be shared across multiple tests.
# They can also help set up and tear down resources needed for the tests.
# `autouse` means that the fixture will be automatically used for all tests in the pytest session,
# so there is no need to explicitly include it in the test functions.


@pytest.fixture(autouse=True)
def run_around_tests():
    """
    Automatically unstub all stubbed methods after each test.

    The 'yield' statement is used to split the fixture function into two parts: the setup
    part that runs before the test, and the teardown part that runs after the test. In this
    case, there is no setup code, so the 'yield' statement directly indicates the end of
    the setup phase and the beginning of the teardown phase.
    """
    # Setup phase: No setup needed in this fixture

    yield

    # Teardown phase: After each test, unstub all stubbed methods
    mockito.unstub()


@pytest.fixture(autouse=True)
async def shutdown_webhooks_listener():
    """
    Automatically shut down the Webhooks listener after each test.
    """
    # Setup phase: No setup needed in this fixture

    yield

    # Teardown phase: After each test, shut down the Webhooks listener
    await Webhooks.shutdown()
