from typing import Any
import core_logging as log

from core_framework.constants import (
    TASK_DEPLOY,
    TASK_RELEASE,
    TASK_TEARDOWN,
    TASK_PLAN,
    TASK_APPLY,
    TASK_COMPILE,
    V_PIPELINE,
    V_DEPLOYSPEC,
)

from .invoker import (
    copy_to_artefacts,
    execute_pipeline_compiler,
    execute_deployspec_compiler,
    execute_runner,
)

from core_framework.models import TaskPayload


def handler(event: dict, context: Any | None = None) -> dict:
    """
    The invoker handler is the entry point for the invoker lambda function.  This function is responsible for
    directing the incoming task to the appropriate execution engine.

    This function returns a Task Response object { "Response": "..." } dictionary.

    Args:
        event (dict): The "Lambda Event" from the requester.
        context (dict): lambda context (Ex: cognito, SQS, SNS, etc). This is where you can get, for example,
                        the lambda runtime lifetime, memory, etc. so you know how long the lambda can run.
                        This is helpful if you have long-running actions and the lambda function will terminate.
                        Better use step functions when running long-running actions.

    Returns:
        dict: The response from the invoker.  This is usually a dictionary with a "Response" key.

    """
    try:
        # event should have been created with TaskPayload.model_dump()
        task_payload = TaskPayload(**event)

        # Setup logging
        log.setup(task_payload.Identity)

        log.info(
            "Invoker started. Executing task: {}-{}",
            task_payload.Task,
            task_payload.Type,
        )

        if task_payload.Type == V_PIPELINE:

            return handle_pipeline(task_payload)

        if task_payload.Type == V_DEPLOYSPEC:

            return handle_deployspec(task_payload)

        raise ValueError("Unsupported task type '{}'".format(task_payload.Type))

    except Exception as e:
        log.error("Error executing task: {}", e)
        raise


def handle_deployspec(task_payload: TaskPayload) -> dict:
    """
    Handle the deployment of a deploy spec.

    Args:
        task_payload (TaskPayload): The task payload object.

    Returns:
        dict: The response from the invoker.  This is usually a dictionary with a "Response" key.

    """
    if task_payload.Task == TASK_COMPILE:

        # Compile the package
        compiler_response = execute_deployspec_compiler(task_payload)

        # MUST return a dictionary { "Response": "..." }
        return compiler_response

    if task_payload.Task == TASK_PLAN:

        compiler_response = {"Error": "Not implemented"}

        # MUST return a dictionary { "Response": "..." }
        return compiler_response

    if task_payload.Task == TASK_APPLY:

        compiler_response = {"Error": "Not implemented"}

        # MUST return a dictionary { "Response": "..." }
        return compiler_response

    if task_payload.Task in [TASK_DEPLOY, TASK_TEARDOWN]:

        # MUST return a dictionary { "Response": "..." }
        return execute_runner(task_payload)

    raise ValueError("Unsupported task '{}'".format(task_payload.Task))


def handle_pipeline(task_payload: TaskPayload) -> dict:
    """
    Handle the deployment of a pipeline.

    Args:
        task_payload (TaskPayload): The task payload object.

    Returns:
        dict: The response from the invoker.  This is usually a dictionary with a "Response" key.

    """
    if task_payload.Task == TASK_COMPILE:
        # Copy package to artefacts bucket / key
        copy_to_artefacts(task_payload)

        # Compile the package
        compiler_response = execute_pipeline_compiler(task_payload)

        # MUST return a dictionary { "Response": "..." }
        return compiler_response

    if task_payload.Task in [TASK_DEPLOY, TASK_RELEASE, TASK_TEARDOWN]:

        # MUST return a dictionary { "Response": "..." }
        return execute_runner(task_payload)

    raise ValueError("Unsupported task '{}'".format(task_payload.Task))
