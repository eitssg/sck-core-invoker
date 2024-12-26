from core_invoker.handler import handler as invoker

from core_framework.models import TaskPayload


def get_event(
    client_name: str, portfolio: str, app: str, branch: str, build: str
) -> TaskPayload:

    arguments: dict = {
        "task": "compile-pipeline",
        "client": client_name,
        "portfolio": portfolio,
        "app": app,
        "branch": branch,
        "build": build,
        "mode": "local",
    }

    return TaskPayload.from_arguments(**arguments)


def test_invoke_lambda():

    event = get_event(
        "test-client", "test-portfolio", "test-app", "test-branch", "test-build"
    )

    response = invoker(event.model_dump(), None)

    assert response is not None

    print()
    print("Invoke Lambda response:")
    print(response)
