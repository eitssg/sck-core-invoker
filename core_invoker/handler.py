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
    Entry point for the invoker Lambda function.

    This function directs the incoming task to the appropriate execution engine
    based on the task type. It returns a Task Response object as a dictionary.

    :param event: The Lambda event, typically created with TaskPayload.model_dump().
    :type event: dict
    :param context: Lambda context object (optional).
    :type context: Any, optional

    :returns: Dictionary with a "Response" key containing the result.
    :rtype: dict

    :raises ValueError: If the task type is unsupported.
    """
    try:
        task_payload = TaskPayload(**event)

        log.set_correlation_id(task_payload.correlation_id)

        log.setup(task_payload.identity)
        log.debug(
            "Invoker started. Executing task: {}-{}",
            task_payload.task,
            task_payload.type,
        )

        if task_payload.type == V_PIPELINE:
            return _handle_pipeline(task_payload)

        if task_payload.type == V_DEPLOYSPEC:
            return _handle_deployspec(task_payload)

        raise ValueError(f"Unsupported task type '{task_payload.type}'")

    except Exception as e:
        log.error("Error executing task: {}", e)
        return {"Response": {"Status": "error", "Message": str(e)}}


def _handle_deployspec(task_payload: TaskPayload) -> dict:
    """
    Handles deployment actions for a deploy spec.

    :param task_payload: The task payload object.
    :type task_payload: TaskPayload

    :returns: Dictionary with a "Response" key containing the result.
    :rtype: dict

    :raises ValueError: If the task is unsupported.
    """
    if task_payload.task == TASK_COMPILE:
        # Compile the package
        compiler_response = execute_deployspec_compiler(task_payload)
        return compiler_response

    if task_payload.task == TASK_PLAN:
        return {"Response": {"Error": "Not implemented"}}

    if task_payload.task == TASK_APPLY:
        return {"Response": {"Error": "Not implemented"}}

    if task_payload.task in [TASK_DEPLOY, TASK_TEARDOWN]:
        return execute_runner(task_payload)

    raise ValueError(f"Unsupported task '{task_payload.task}'")


def _handle_pipeline(task_payload: TaskPayload) -> dict:
    """
    Handles deployment actions for a pipeline.

    :param task_payload: The task payload object.
    :type task_payload: TaskPayload

    :returns: Dictionary with a "Response" key containing the result.
    :rtype: dict

    :raises ValueError: If the task is unsupported.
    """
    if task_payload.task == TASK_COMPILE:
        # Copy package to artefacts bucket / key
        copy_to_artefacts(task_payload)
        # Compile the package
        compiler_response = execute_pipeline_compiler(task_payload)
        return compiler_response

    if task_payload.task in [TASK_DEPLOY, TASK_RELEASE, TASK_TEARDOWN]:
        return execute_runner(task_payload)

    raise ValueError(f"Unsupported task '{task_payload.task}'")
