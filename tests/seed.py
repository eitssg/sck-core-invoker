import pytest

import core_framework as util

from core_db.registry.client import ClientFactsModel, ClientFactsFactory
from core_db.registry.portfolio import (
    PortfolioFactsModel,
    PortfolioFactsFactory,
    ContactFacts,
    ApproverFacts,
    ProjectFacts,
    OwnerFacts,
)
from core_db.registry.app import AppFactsModel, AppFactsFactory
from core_db.registry.zone import (
    ZoneFactsModel,
    ZoneFactsFactory,
    AccountFacts,
    RegionFacts,
    KmsFacts,
    SecurityAliasFacts,
    ProxyFacts,
)

from .bootstrap import *
from .arguments import *


@pytest.fixture(scope="module")
def client_data(bootstrap_dynamo: bool, organization: dict, arguments: dict) -> ClientFactsModel:
    """
    Create and save ClientFactsModel test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param organization: Organization information
    :type organization: dict
    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created ClientFactsModel instance
    :rtype: ClientFactsModel
    """
    assert bootstrap_dynamo
    assert isinstance(organization, dict)
    assert isinstance(arguments, dict)

    client = arguments["client"]

    region = util.get_region()
    bucket_name = util.get_bucket_name()

    aws_account_id = organization["account_id"]

    clients = ClientFactsFactory.get_model(client, True)
    cf = clients(
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
def portfolio_data(bootstrap_dynamo: bool, client_data: ClientFactsModel, arguments: dict) -> PortfolioFactsModel:
    """
    Create and save PortfolioFactsModel test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param client_data: ClientFactsModel instance
    :type client_data: ClientFactsModel
    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created PortfolioFactsModel instance
    :rtype: PortfolioFactsModel
    """
    assert bootstrap_dynamo
    assert isinstance(client_data, ClientFactsModel)
    assert isinstance(arguments, dict)

    portfolio_name = arguments["portfolio"]

    # PynamoDB: PascalCase attribute access
    domain_name = client_data.Domain
    client = client_data.Client

    portfolios = PortfolioFactsFactory.get_model(client)
    portfolio = portfolios(
        Client=client_data.Client,  # PynamoDB: PascalCase attributes
        Portfolio=portfolio_name,
        Contacts=[ContactFacts(Name="John Doe", Email="john.doe@example.com")],
        Approvers=[
            ApproverFacts(
                Name="Jane Doe",
                Email="jane.doe@example.com",
                Roles=["admin"],
                Sequence=1,
            )
        ],
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
def zone_data(bootstrap_dynamo: bool, client_data: ClientFactsModel) -> ZoneFactsModel:
    """
    Create and save ZoneFactsModel test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param client_data: ClientFactsModel instance
    :type client_data: ClientFactsModel
    :returns: Created ZoneFactsModel instance
    :rtype: ZoneFactsModel
    """
    assert bootstrap_dynamo
    assert isinstance(client_data, ClientFactsModel)

    # PynamoDB: PascalCase attribute access
    automation_account_id = client_data.AutomationAccount
    automation_account_name = client_data.OrganizationName

    client = client_data.Client

    zone_label = "my-automation-service-zone"

    zones = ZoneFactsFactory.get_model(client)
    zone = zones(
        Client=client_data.Client,  # PynamoDB: PascalCase attributes
        Zone=zone_label,
        AccountFacts=AccountFacts(  # PynamoDB: PascalCase attributes
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
            "sin": RegionFacts(
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
    portfolio_data: PortfolioFactsModel,
    zone_data: ZoneFactsModel,
    client_data: ClientFactsModel,
    arguments: dict,
) -> AppFactsModel:
    """
    Create and save AppFactsModel test data.

    :param bootstrap_dynamo: Bootstrap completion status
    :type bootstrap_dynamo: bool
    :param portfolio_data: PortfolioFactsModel instance
    :type portfolio_data: PortfolioFactsModel
    :param zone_data: ZoneFactsModel instance
    :type zone_data: ZoneFactsModel
    :param arguments: Test arguments
    :type arguments: dict
    :returns: Created AppFactsModel instance
    :rtype: AppFactsModel
    """
    assert bootstrap_dynamo
    assert isinstance(portfolio_data, PortfolioFactsModel)
    assert isinstance(zone_data, ZoneFactsModel)
    assert isinstance(arguments, dict)

    client = client_data.Client

    portfolio = arguments["portfolio"]
    app_name = arguments["app"]

    # The client/portfolio is where this BizApp that this Deployment is for.
    # The Zone is where this BizApp component will be deployed.

    apps = AppFactsFactory.get_model(client)
    app_facts = apps(
        Portfolio=portfolio_data.portfolio,  # PynamoDB: PascalCase attributes
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
