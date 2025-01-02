from typing import OrderedDict
import core_logging as log

import core_framework as util
from core_framework.constants import TR_RESPONSE, OBJ_ARTEFACTS, V_SERVICE

import core_helper.aws as aws

from core_component.handler import handler as component_compiler_handler
from core_deployspec.handler import handler as deployspec_compiler_handler
from core_runner.handler import handler as runner_handler

from core_framework.models import TaskPayload
from core_helper.magic import MagicS3Client


def execute_pipeline_compiler(task_payload: TaskPayload) -> dict:
    """
    Execute the pipeline compiler lambda function

    Args:
        package_details (dict): the package details object
        deployment_details (dict): the deployment details object

    Returns:
        dict: the results of the component compiler
    """
    log.info("Invoking pipeline compiler")

    arn = util.get_component_compiler_lambda_arn()

    if util.is_local_mode():
        response = component_compiler_handler(task_payload.model_dump(), None)
    else:
        response = aws.invoke_lambda(arn, task_payload.model_dump())

    if TR_RESPONSE not in response:
        raise RuntimeError(
            "Pipeline compiler response does not contain a response: {}".format(response)
        )

    return response[TR_RESPONSE]


def execute_deployspec_compiler(task_payload: TaskPayload) -> dict:
    """
    Execute the deployspec compiler Lambda function

    Args:
        task_payload (TaskPayload): the task definition

    Returns:
        dict: the results of the deployspec compile
    """
    log.info("Invoking deployspec compiler")

    arn = util.get_deployspec_compiler_lambda_arn()

    if util.is_local_mode():
        response = deployspec_compiler_handler(task_payload.model_dump(), None)
    else:
        response = aws.invoke_lambda(arn, task_payload.model_dump())

    if TR_RESPONSE not in response:
        raise RuntimeError(
            "Deployspec compiler response does not contain a response: {}".format(
                response
            )
        )

    return response[TR_RESPONSE]


def execute_runner(task_payload: TaskPayload) -> dict:
    """
    Execute the runner step functions

    It is assumed that task_payload is fully populated with the
    location of the files for Package, Action, and State artefacts.

    The "Task Response" is a dictionary { "Response": "..." }

    Args:
        task_payload (TaskPayload): the task definition.

    Returns:
        dict: Tasc Response results of the runner start request
    """
    log.info("Invoking runner")

    arn = util.get_start_runner_lambda_arn()

    if util.is_local_mode():
        response = runner_handler(task_payload.model_dump(), None)
    else:
        response = aws.invoke_lambda(arn, task_payload.model_dump())

    if TR_RESPONSE not in response:
        raise RuntimeError(
            "Runner response does not contain a response: {}".format(response)
        )

    return response


def copy_to_artefacts(task_payload: TaskPayload) -> dict:
    """
    Copies the packages to the artefacts bucket

    Args:
        task_payload (TaskPayload): The task payload

    Raises:
        RuntimeError: Something unexpected happened
        ValueError: Package key not found in task payload

    Returns:
        dict: results of the copy
    """

    artefact_bucket_region = util.get_artefact_bucket_region()
    artefact_bucket_name = util.get_artefact_bucket_name()

    package = task_payload.Package
    if package.BucketRegion != artefact_bucket_region:
        raise RuntimeError(
            artefact_bucket_region,
            "Source S3 bucket must be in region '{}'".format(artefact_bucket_region),
        )
    if not package.Key:
        raise ValueError("Package key not found in task payload")

    object_name = package.get_name()

    dd = task_payload.DeploymentDetails
    destination_key = dd.get_object_key(
        OBJ_ARTEFACTS, object_name, s3=package.Mode == V_SERVICE
    )

    copy_source = {"Bucket": package.BucketName, "Key": package.Key, "VersionId": None}

    destination = {
        "Bucket": artefact_bucket_name,
        "Key": destination_key,
        "VersionId": None,
    }

    log.info(
        "Copying object to artefacts",
        details=OrderedDict([("Source", copy_source), ("Destination", destination)]),
    )

    artefact_bucket = MagicS3Client.get_bucket(
        Region=artefact_bucket_region, BucketName=artefact_bucket_name
    )

    destination_object = artefact_bucket.Object(destination_key)

    # Copy the object
    response = destination_object.copy_from(
        ACL="bucket-owner-full-control",
        CopySource=copy_source,
        ServerSideEncryption="AES256",
    )

    if "Error" in response:
        raise Exception(
            "Error copying object to artefacts: {}".format(response["Error"])
        )

    return response
