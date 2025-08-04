import pytest

import core_framework as util


@pytest.fixture(scope="module")
def arguments() -> dict:
    """
    Provide test arguments for the invoker tests.

    :returns: Dictionary of test arguments
    :rtype: dict
    """
    return {
        "task": "compile",
        "client": util.get_client(),
        "portfolio": "test-portfolio",
        "app": "test-app",
        "branch": "main",
        "build": "latest",
    }
