"""
Unit tests for the core invoker functionality.

This module contains pytest test cases for the invoker handler,
including setup of test data and validation of different task types.
"""

import pytest
import os
import core_framework as util

import core_helper.aws as aws

from core_framework.models import TaskPayload

from core_db.event import EventModel
from core_db.item import ItemModel
from core_db.registry.client import ClientFacts
from core_db.registry.portfolio import (
    PortfolioFacts,
    ContactFacts,
    ApproverFacts,
    ProjectFacts,
    OwnerFacts,
)
from core_db.registry.app import AppFacts
from core_db.registry.zone import (
    ZoneFacts,
    AccountFacts as AccountFactsModel,
    RegionFacts as RegionFactsModel,
    KmsFacts,
    SecurityAliasFacts,
    ProxyFacts,
)
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


@pytest.fixture(scope="module")
def arguments() -> dict:
    """
    Test arguments for task payload creation.

    :returns: Dictionary containing test parameters
    :rtype: dict
    """
    client = util.get_client()
    portfolio = "my-portfolio"
    app = "my-app"
    branch = "my-branch"
    build = "dp-build"

    args = {
        "task": "compile",
        "client": client,
        "portfolio": portfolio,
        "app": app,
        "branch": branch,
        "build": build,
    }

    return args


@pytest.fixture(scope="module")
def bootstrap_dynamo() -> bool:
    """
    Bootstrap DynamoDB tables for testing.

    :returns: True if bootstrap successful
    :rtype: bool
    :raises AssertionError: If DynamoDB setup fails
    """
    # see environment variables in .env
    host = util.get_dynamodb_host()

    assert host == "http://localhost:8000", "DYNAMODB_HOST must be set to http://localhost:8000"

    try:
        if not EventModel.exists():
            EventModel.create_table(wait=True)

        if not ItemModel.exists():
            ItemModel.create_table(wait=True)

        if not ClientFacts.exists():
            ClientFacts.create_table(wait=True)

        if not PortfolioFacts.exists():
            PortfolioFacts.create_table(wait=True)

        if not AppFacts.exists():
            AppFacts.create_table(wait=True)

        # Check if ZoneFacts exists before trying to delete
        if ZoneFacts.exists():
            ZoneFacts.delete_table()

        if not ZoneFacts.exists():
            ZoneFacts.create_table(wait=True)

    except Exception as e:
        print(f"Error bootstrapping DynamoDB: {e}")
        assert False, f"Failed to bootstrap DynamoDB: {e}"

    return True


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
def client_data(bootstrap_dynamo: bool, organization: dict, arguments: dict) -> ClientFacts:
    """
    Create and save ClientFacts test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param organization: Organization information
    :type organization: dict
    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created ClientFacts instance
    :rtype: ClientFacts
    """
    assert bootstrap_dynamo
    assert isinstance(organization, dict)
    assert isinstance(arguments, dict)

    client = arguments["client"]

    region = util.get_region()
    bucket_name = util.get_bucket_name()

    aws_account_id = organization["account_id"]

    cf = ClientFacts(
        Client=client,  # PynamoDB: PascalCase attributes
        Domain="my-domain.com",
        OrganizationId=organization["id"],
        OrganizationName=organization["name"],
        OrganizationAccount=organization["account_id"],
        OrganizationEmail=organization["email"],
        ClientRegion=region,
        MasterRegion=region,
        AutomationAccount=aws_account_id,
        BucketName=bucket_name,
        BucketRegion=region,
        AuditAccount=aws_account_id,
        DocsBucketName=bucket_name,
        SecurityAccount=aws_account_id,
        UiBucket=bucket_name,
        Scope="",
    )
    cf.save()

    return cf


@pytest.fixture(scope="module")
def portfolio_data(bootstrap_dynamo: bool, client_data: ClientFacts, arguments: dict) -> PortfolioFacts:
    """
    Create and save PortfolioFacts test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param client_data: ClientFacts instance
    :type client_data: ClientFacts
    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created PortfolioFacts instance
    :rtype: PortfolioFacts
    """
    assert bootstrap_dynamo
    assert isinstance(client_data, ClientFacts)
    assert isinstance(arguments, dict)

    portfolio_name = arguments["portfolio"]

    # PynamoDB: PascalCase attribute access
    domain_name = client_data.Domain

    portfolio = PortfolioFacts(
        Client=client_data.Client,  # PynamoDB: PascalCase attributes
        Portfolio=portfolio_name,
        Contacts=[ContactFacts(Name="John Doe", Email="john.doe@example.com")],
        Approvers=[ApproverFacts(Name="Jane Doe", Email="jane.doe@example.com", Roles=["admin"], Sequence=1)],
        Project=ProjectFacts(Name="my-project", Description="my project description", Code="MYPRJ"),
        Bizapp=ProjectFacts(Name="my-bizapp", Description="my bizapp description", Code="MYBIZ"),
        Owner=OwnerFacts(Name="John Doe", Email="john.doe@example.com"),
        Domain=f"my-app.{domain_name}",
        Tags={
            "BizApp": "MyBizApp",
            "Manager": "John Doe",
        },
        Metadata={
            "misc": "items",
            "date": "2021-01-01",
        },
    )
    portfolio.save()

    return portfolio


@pytest.fixture(scope="module")
def zone_data(bootstrap_dynamo: bool, client_data: ClientFacts) -> ZoneFacts:
    """
    Create and save ZoneFacts test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param client_data: ClientFacts instance
    :type client_data: ClientFacts
    :returns: Created ZoneFacts instance
    :rtype: ZoneFacts
    """
    assert bootstrap_dynamo
    assert isinstance(client_data, ClientFacts)

    # PynamoDB: PascalCase attribute access
    automation_account_id = client_data.AutomationAccount
    automation_account_name = client_data.OrganizationName

    zone_label = "my-automation-service-zone"

    zone = ZoneFacts(
        Client=client_data.Client,  # PynamoDB: PascalCase attributes
        Zone=zone_label,
        AccountFacts=AccountFactsModel(  # PynamoDB: PascalCase attributes
            Client=client_data.Client,
            AwsAccountId=automation_account_id,
            OrganizationalUnit="PrimaryUnit",
            AccountName=automation_account_name,
            Environment="prod",
            Kms=KmsFacts(
                AwsAccountId=automation_account_id,
                KmsKeyArn="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012",
                KmsKey="alias/my-kms-key",
                DelegateAwsAccountIds=[automation_account_id],
            ),
            ResourceNamespace="my-automation-service",
            NetworkName="my-network-from-ciscos",
            VpcAliases={
                "primary-network": "my-cisco-network-primary-network-id",
                "secondary-network": "my-cisco-network-secondary-network-id",
            },
            SubnetAliases={
                "ingress": "my-cisco-network-ingress-subnet-id",
                "workload": "my-cisco-network-workload-subnet-id",
                "egress": "my-cisco-network-egress-subnet-id",
            },
            Tags={"Zone": "my-automation-service-zone"},
        ),
        RegionFacts={
            "sin": RegionFactsModel(
                AwsRegion="ap-southeast-1",
                AzCount=3,
                ImageAliases={"imageid:latest": "ami-2342342342344"},
                MinSuccessfulInstancesPercent=100,
                SecurityAliases={
                    "global_cidrs": [
                        SecurityAliasFacts(
                            Type="cidr",  # PynamoDB: PascalCase attributes
                            Value="192.168.0.0/16",
                            Description="Global CIDR 1",
                        ),
                        SecurityAliasFacts(Type="cidr", Value="10.0.0.0/8", Description="Global CIDR 2"),
                    ]
                },
                SecurityGroupAliases={
                    "alias1": "aws_sg_ingress",
                    "alias2": "aws-sg-egress-groups",
                },
                Proxy=[
                    ProxyFacts(
                        Host="myproxy.proxy.com",
                        Port=8080,
                        Url="http://proxy.acme.com:8080",
                        NoProxy="10.0.0.0/8,192.168.0.0/16,*.acme.com",
                    )
                ],
                ProxyHost="myproxy.proxy.com",
                ProxyPort=8080,
                ProxyUrl="http://proxy.acme.com:8080",
                NoProxy="127.0.0.1,localhost,*.acme.com",
                NameServers=["192.168.1.1"],
                Tags={"Region": "sin"},
            )
        },
        Tags={"Zone": zone_label},
    )
    zone.save()

    return zone


@pytest.fixture(scope="module")
def app_data(
    bootstrap_dynamo: bool,
    portfolio_data: PortfolioFacts,
    zone_data: ZoneFacts,
    arguments: dict,
) -> AppFacts:
    """
    Create and save AppFacts test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param portfolio_data: PortfolioFacts instance
    :type portfolio_data: PortfolioFacts
    :param zone_data: ZoneFacts instance
    :type zone_data: ZoneFacts
    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created AppFacts instance
    :rtype: AppFacts
    """
    assert bootstrap_dynamo
    assert isinstance(portfolio_data, PortfolioFacts)
    assert isinstance(zone_data, ZoneFacts)
    assert isinstance(arguments, dict)

    portfolio = arguments["portfolio"]
    app_name = arguments["app"]

    # The client/portfolio is where this BizApp that this Deployment is for.
    # The Zone is where this BizApp component will be deployed.

    app_facts = AppFacts(
        ClientPortfolio=portfolio_data.get_client_portfolio_key(),  # PynamoDB: PascalCase attributes
        AppRegex=f"^prn:{portfolio}:{app_name}:.*:.*$",
        Zone=zone_data.Zone,  # PynamoDB: PascalCase attribute access
        Name="test application",
        Environment="prod",
        ImageAliases={"image1": "awsImageID1234234234"},
        Repository="https://github.com/my-org/my-portfolio-my-app.git",
        Region="sin",
        Tags={"Disposition": "Testing"},
        Metadata={"misc": "items"},
    )

    app_facts.save()

    return app_facts


@pytest.fixture(scope="module")
def task_payload(arguments: dict) -> TaskPayload:
    """
    Create TaskPayload for testing.

    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created TaskPayload instance
    :rtype: TaskPayload
    """
    task_payload = TaskPayload.from_arguments(**arguments)

    # TaskPayload is Pydantic: snake_case attributes
    pkg = task_payload.package

    # UPLOAD action to upload our package to the system
    # PackageDetails is Pydantic: snake_case attributes
    zipfilename = os.path.join(pkg.data_path, pkg.bucket_name, pkg.key)
    os.makedirs(os.path.dirname(zipfilename), exist_ok=True)

    if os.path.exists(zipfilename):
        os.remove(zipfilename)

    dirname = os.path.dirname(os.path.realpath(__file__))
    # create or update our test package zip with our test deployspec.yaml file.
    os.system(f"cd {dirname} && 7z a {zipfilename} components/* vars/*")

    return task_payload


@pytest.fixture(scope="module")
def facts_data(
    bootstrap_dynamo: bool,
    task_payload: TaskPayload,
    client_data: ClientFacts,
    portfolio_data: PortfolioFacts,
    zone_data: ZoneFacts,
    app_data: AppFacts,
):
    """
    Get facts data for testing.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param task_payload: TaskPayload instance
    :type task_payload: TaskPayload
    :param client_data: ClientFacts instance
    :type client_data: ClientFacts
    :param portfolio_data: PortfolioFacts instance
    :type portfolio_data: PortfolioFacts
    :param zone_data: ZoneFacts instance
    :type zone_data: ZoneFacts
    :param app_data: AppFacts instance
    :type app_data: AppFacts
    :returns: Facts dictionary
    :rtype: dict
    """
    assert bootstrap_dynamo
    assert isinstance(task_payload, TaskPayload)
    assert isinstance(client_data, ClientFacts)
    assert isinstance(portfolio_data, PortfolioFacts)
    assert isinstance(zone_data, ZoneFacts)
    assert isinstance(app_data, AppFacts)

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

    task_payload.task = TASK_COMPILE
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_ds_plan(task_payload: TaskPayload, facts_data: dict):
    """Test deployspec plan task."""
    assert facts_data is not None

    task_payload.task = TASK_PLAN
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_ds_apply(task_payload: TaskPayload, facts_data: dict):
    """Test deployspec apply task."""
    assert facts_data is not None

    task_payload.task = TASK_APPLY
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_ds_deploy(task_payload: TaskPayload):
    """Test deployspec deploy task."""
    task_payload.task = TASK_DEPLOY
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_ds_teardown(task_payload: TaskPayload):
    """Test deployspec teardown task."""
    task_payload.task = TASK_TEARDOWN
    task_payload.type = V_DEPLOYSPEC

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_compile(task_payload: TaskPayload, facts_data: dict):
    """Test pipeline compile task."""
    assert facts_data is not None

    task_payload.task = TASK_COMPILE
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_deploy(task_payload: TaskPayload):
    """Test pipeline deploy task."""
    task_payload.task = TASK_DEPLOY
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_release(task_payload: TaskPayload):
    """Test pipeline release task."""
    task_payload.task = TASK_RELEASE
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_pl_teardown(task_payload: TaskPayload):
    """Test pipeline teardown task."""
    task_payload.task = TASK_TEARDOWN
    task_payload.type = V_PIPELINE

    response = invoker(task_payload.model_dump(), None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"
