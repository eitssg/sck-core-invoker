from typing import Any
import core_logging as log

from core_framework.constants import (
    TASK_DEPLOY,
    TASK_RELEASE,
    TASK_TEARDOWN,
    TASK_PLAN,
    TASK_APPLY,
    TASK_COMPILE_PIPELINE,
    TASK_COMPILE_DEPLOYSPEC,
)

from .invoker import (
    copy_to_artefacts,
    execute_pipeline_compiler,
    execute_deployspec_compiler,
    execute_runner,
)

from core_framework.models import TaskPayload


def handler(event: dict, context: Any | None = None) -> dict:

    try:
        # event should have been created with TaskPayload.model_dump()
        task_payload = TaskPayload(**event)

        # Setup logging
        log.setup(task_payload.Identity)

        if task_payload.Task == TASK_COMPILE_PIPELINE:

            # Copy package to artefacts bucket / key
            copy_to_artefacts(task_payload)

            # Compile the package
            compiler_response = execute_pipeline_compiler(task_payload)

            return compiler_response

        if task_payload.Task == TASK_COMPILE_DEPLOYSPEC:

            # Copy package to artefacts bucket / key
            copy_to_artefacts(task_payload)

            # Compile the package
            compiler_response = execute_deployspec_compiler(task_payload)

            return compiler_response

        if task_payload.Task == TASK_PLAN:

            copy_to_artefacts(task_payload)

            compiler_response = {"Error": "Not implemented"}

            return compiler_response

        if task_payload.Task in [
            TASK_DEPLOY,
            TASK_APPLY,
            TASK_RELEASE,
            TASK_TEARDOWN
        ]:

            return execute_runner(task_payload)

        raise ValueError("Unsupported task '{}'".format(task_payload.Task))

    except Exception as e:
        log.error("Error executing task: {}", e)
        raise
