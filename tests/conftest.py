import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(autouse=True)  # for all tests in the test suite
def prefect_db():
    with prefect_test_harness():
        """sets up a temp sandbox prefect database/server for running tests against"""
        yield
