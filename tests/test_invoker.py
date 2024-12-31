import pytest
import os
import re
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
    TASK_COMPILE_DEPLOYSPEC,
    TASK_COMPILE_PIPELINE,
    TASK_DEPLOY,
    TASK_APPLY,
    TASK_RELEASE,
    TASK_TEARDOWN,
    TASK_PLAN,
)


@pytest.fixture(scope="module")
def bootstrap_dynamo():

    # see environment variables in .env
    host = util.get_dynamodb_host()

    assert (
        host == "http://localhost:8000"
    ), "DYNAMODB_HOST must be set to http://localhost:8000"

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

        if ZoneFacts.exists():
            ZoneFacts.delete_table()

        if not ZoneFacts.exists():
            ZoneFacts.create_table(wait=True)

    except Exception as e:
        print(e)
        assert False

    return True


@pytest.fixture(scope="module")
def organization(**kwargs) -> dict:
    """Return organization information for the AWS Profile"""
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
def client_data(bootstrap_dynamo, organization: dict) -> ClientFacts:

    client = util.get_client()
    region = util.get_region()
    bucket_name = util.get_bucket_name()

    aws_account_id = organization["account_id"]

    cf = ClientFacts(
        client=client,
        domain="my-domain.com",
        organization_id=organization["id"],
        organization_name=organization["name"],
        organization_account=organization["account_id"],
        organization_email=organization["email"],
        client_region=region,
        master_region=region,
        automation_account=aws_account_id,
        automation_bucket=bucket_name,
        automation_bucket_region=region,
        audit_account=aws_account_id,
        docs_bucket=bucket_name,
        security_account=aws_account_id,
        ui_bucket=bucket_name,
        scope_prefix="",
    )
    cf.save()

    return cf


@pytest.fixture(scope="module")
def portfolio_data(bootstrap_dynamo, client_data: ClientFacts) -> PortfolioFacts:

    portfllio_name = "my-portfolio"
    domain_name = client_data.Domain

    portfolio = PortfolioFacts(
        Client=client_data.Client,
        Portfolio=portfllio_name,
        Contacts=[ContactFacts(name="John Doe", email="john.doe@tmail.com")],
        Approvers=[
            ApproverFacts(
                name="Jane Doe", email="john.doe@tmail.com", roles=["admin"], sequence=1
            )
        ],
        Project=ProjectFacts(
            name="my-project", description="my project description", code="MYPRJ"
        ),
        Bizapp=ProjectFacts(
            name="my-bizapp", description="my bizapp description", code="MYBIZ"
        ),
        Owner=OwnerFacts(name="John Doe", email="john.doe@tmail.com"),
        Domain=f"my-app.{domain_name}",
        Tags={
            "BizzApp": "MyBizApp",
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
def zone_data(bootstrap_dynamo, client_data: ClientFacts) -> ZoneFacts:

    automation_account_id = client_data.AutomationAccount
    automation_account_name = client_data.OrganizationName
    zone = ZoneFacts(
        Client=client_data.Client,
        Zone="my-automation-service-zone",
        AccountFacts=AccountFactsModel(
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
                            Type="cidr",
                            Value="192.168.0.0/16",
                            Description="Global CIDR 1",
                        ),
                        SecurityAliasFacts(
                            Type="cidr", Value="10.0.0.0/8", Description="Global CIDR 2"
                        ),
                    ]
                },
                SecurityGroupAliases={
                    "alias1": "aws_sg_ingress",
                    "alias2": "aws-sg-egress-groups",
                },
                Proxy=[
                    ProxyFacts(
                        Host="myprox.proxy.com",
                        Port=8080,
                        Url="http://proxy.acme.com:8080",
                        NoProxy="10.0.0.0/8,192.168.0.0/16,*acme.com",
                    )
                ],
                ProxyHost="myprox.proxy.com",
                ProxyPort=8080,
                ProxyUrl="http://proxy.acme.com:8080",
                NoProxy="127.0.0.1,localhost,*.acme.com",
                NameServers=["192.168.1.1"],
                Tags={"Region": "sin"},
            )
        },
        Tags={"Zone": "my-automation-service-zone"},
    )
    zone.save()

    return zone


@pytest.fixture(scope="module")
def app_data(
    bootstrap_dynamo, portfolio_data: PortfolioFacts, zone_data: ZoneFacts
) -> AppFacts:

    # The client/portfolio is where this BizApp that this Deployment is for.
    # The Zone is where this BizApp component will be deployed.

    app = AppFacts(
        ClientPortfolio=portfolio_data.get_client_portfolio_key(),
        AppRegex="^prn:my-portfolio:my-app:.*:.*$",
        Zone=zone_data.Zone,
        Name="test application",
        Environment="prod",
        ImageAliases={"image1": "awsImageID1234234234"},
        Repository="https://github.com/my-org/my-portfolio-my-app.git",
        Region="sin",
        Tags={"Disposition": "Testing"},
        Metadata={"misc": "items"},
    )

    app.save()

    return app


@pytest.fixture(scope="module")
def task_payload(bootstrap_dynamo, portfolio_data: PortfolioFacts, app_data: AppFacts) -> TaskPayload:

    app_search_regex = app_data.AppRegex

    arguments: dict = {
        "portfolio": portfolio_data.Portfolio,
        "app": "my-app",
        "branch": "dev-branch",
        "build": "build-1",
    }

    task_payload = TaskPayload.from_arguments(**arguments)

    identity = task_payload.Identity

    assert re.match(app_search_regex, identity)

    pkg = task_payload.Package

    # UPLOAD action to upload our package to the system
    zipfilename = os.path.join(pkg.AppPath, pkg.BucketName, pkg.Key)
    os.makedirs(os.path.dirname(zipfilename), exist_ok=True)

    if os.path.exists(zipfilename):
        os.remove(zipfilename)

    dirname = os.path.dirname(os.path.realpath(__file__))
    # create or update our test package zip with our test deployspec.yaml file.
    os.system(f"cd {dirname} && 7z a {zipfilename} components/* vars/*")

    return task_payload


@pytest.fixture(scope="module")
def facts_data(
    bootstrap_dynamo,
    task_payload: TaskPayload,
    client_data: ClientFacts,
    portfolio_data: PortfolioFacts,
    zone_data: ZoneFacts,
    app_data: AppFacts,
):

    deployment_details = task_payload.DeploymentDetails

    facts = get_facts(deployment_details)

    assert facts is not None

    assert facts["Client"] == client_data.Client
    assert facts["Portfolio"] == portfolio_data.Portfolio
    assert facts["Name"] == app_data.Name
    assert facts["Environment"] == app_data.Environment
    assert facts["Zone"] == zone_data.Zone

    return facts


def test_compile_pipeline(task_payload: TaskPayload, facts_data: dict):

    assert facts_data is not None

    task_payload.Task = TASK_COMPILE_PIPELINE

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_compile_deployspec(task_payload: TaskPayload):

    task_payload.Task = TASK_COMPILE_DEPLOYSPEC

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_plan(task_payload: TaskPayload):

    task_payload.Task = TASK_PLAN

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_appy(task_payload: TaskPayload):

    task_payload.Task = TASK_APPLY

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_deploy(task_payload: TaskPayload):

    task_payload.Task = TASK_DEPLOY

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_release(task_payload: TaskPayload):

    task_payload.Task = TASK_RELEASE

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"


def test_run_teardown(task_payload: TaskPayload):

    task_payload.Task = TASK_TEARDOWN

    event = task_payload.model_dump()
    response = invoker(event, None)

    assert response is not None
    assert "Error" in response
    assert response["Error"] == "Not implemented"
