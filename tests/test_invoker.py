"""
Unit tests for the core invoker functionality.

This module contains pytest test cases for the invoker handler,
including setup of test data and validation of different task types.
"""

import pytest
import core_framework as util

import core_logging as log
import core_helper.aws as aws

from core_framework.models import TaskPayload

from core_db.registry.client import ClientFactsModel
from core_db.registry.portfolio import PortfolioFactsModel
from core_db.registry.app import AppFactsModel
from core_db.registry.zone import ZoneFactsModel

from core_db.facter import get_facts

from core_invoker.handler import handler as invoker

from core_framework.constants import (
    TASK_DEPLOY,
    TASK_APPLY,
    TASK_RELEASE,
    TASK_TEARDOWN,
    TASK_PLAN,
    TASK_COMPILE,
    V_PIPELINE,
    V_DEPLOYSPEC,
)

from .conftest import *
from .bootstrap import *
from .seed import *
from .arguments import *
from .package import *


@pytest.fixture(scope="module")
def organization() -> dict:
    """
    Return organization information for the AWS Profile.

    :returns: Dictionary containing organization details
    :rtype: dict
    """
    organization = {"id": "", "account_id": "", "name": "", "email": ""}
    try:
        client = aws.org_client()
        orginfo = client.describe_organization()
        org = orginfo.get("Organization", {})
        organization.update(
            {
                "id": org.get("Id", ""),
                "account_id": org.get("MasterAccountId", ""),
                "email": org.get("MasterAccountEmail", ""),
            }
        )

        if organization["account_id"]:
            response = client.describe_account(AccountId=organization["account_id"])
            organization["name"] = response.get("Account", {}).get("Name", "")

    except Exception:  # pylint: disable=broad-except
        pass

    return organization


@pytest.fixture(scope="module")
def task_payload(arguments: dict) -> TaskPayload:
    """
    Create TaskPayload for testing.

    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created TaskPayload instance
    :rtype: TaskPayload
    """

    # consider args = argparse.parse_args()
    # then once we have args, being it's a very flat structure, we can use it to create the TaskPayload
    # for example:
    # task_payload = TaskPayload.from_arguments(**args)

    task_payload = TaskPayload.from_arguments(**arguments)

    upload_package(task_payload.package)

    return task_payload


@pytest.fixture(scope="module")
def facts_data(
    bootstrap_dynamo: bool,
    task_payload: TaskPayload,
    client_data: ClientFactsModel,
    portfolio_data: PortfolioFactsModel,
    zone_data: ZoneFactsModel,
    app_data: AppFactsModel,
):
    """
    Get facts data for testing.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param task_payload: TaskPayload instance
    :type task_payload: TaskPayload
    :param client_data: ClientFactsModel instance
    :type client_data: ClientFactsModel
    :param portfolio_data: PortfolioFactsModel instance
    :type portfolio_data: PortfolioFactsModel
    :param zone_data: ZoneFactsModel instance
    :type zone_data: ZoneFactsModel
    :param app_data: AppFactsModel instance
    :type app_data: AppFactsModel
    :returns: Facts dictionary
    :rtype: dict
    """
    assert bootstrap_dynamo
    assert isinstance(task_payload, TaskPayload)
    assert isinstance(client_data, ClientFactsModel)
    assert isinstance(portfolio_data, PortfolioFactsModel)
    assert isinstance(zone_data, ZoneFactsModel)
    assert isinstance(app_data, AppFactsModel)

    # TaskPayload is Pydantic: snake_case attribute
    deployment_details = task_payload.deployment_details

    facts = get_facts(deployment_details)

    assert facts is not None

    # Facts dict has PascalCase keys, PynamoDB models have PascalCase attributes
    assert facts["Client"] == client_data.Client
    assert facts["Portfolio"] == portfolio_data.Portfolio
    assert facts["Name"] == app_data.Name
    assert facts["Environment"] == app_data.Environment
    assert facts["Zone"] == zone_data.Zone

    return facts


def test_run_ds_compile(task_payload: TaskPayload, facts_data: dict):
    """Test deployspec compile task."""
    assert facts_data is not None

    upload_package(task_payload.package)

    task_payload.set_task(TASK_COMPILE)
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" not in response
    assert "Status" in response
    assert response["Status"] == "COMPILE_COMPLETE"


def test_run_ds_plan(task_payload: TaskPayload, facts_data: dict):
    """Test deployspec plan task."""
    assert facts_data is not None

    task_payload.set_task(TASK_PLAN)
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_ds_apply(task_payload: TaskPayload, facts_data: dict):
    """Test deployspec apply task."""
    assert facts_data is not None

    task_payload.set_task(TASK_APPLY)
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_ds_deploy(task_payload: TaskPayload):
    """Test deployspec deploy task."""

    task_payload.set_task(TASK_DEPLOY)
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert "Status" in response
    assert response["Status"] == "COMPILE_COMPLETE"


def test_run_ds_teardown(task_payload: TaskPayload):
    """Test deployspec teardown task."""
    task_payload.set_task(TASK_TEARDOWN)
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_compile(task_payload: TaskPayload, facts_data: dict):
    """Test pipeline compile task."""
    assert facts_data is not None

    task_payload.set_task(TASK_COMPILE)
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_deploy(task_payload: TaskPayload):
    """Test pipeline deploy task."""
    task_payload.set_task(TASK_DEPLOY)
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_release(task_payload: TaskPayload):
    """Test pipeline release task."""
    task_payload.set_task(TASK_RELEASE)
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_teardown(task_payload: TaskPayload):
    """Test pipeline teardown task."""
    task_payload.set_task(TASK_TEARDOWN)
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"
