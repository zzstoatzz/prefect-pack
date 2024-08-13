import os
import subprocess
from typing import Any

from prefect.events import Event, emit_event


def get_client_id():
    """hostname and pid of the client"""
    return f"{os.uname().nodename}-{os.getpid()}"


def get_git_context():
    try:
        cmds = {
            "branch": ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            "remote": ["git", "config", "--get", "remote.origin.url"],
            "commit": ["git", "rev-parse", "HEAD"],
            "root": ["git", "rev-parse", "--show-toplevel"],
        }
        return {
            k: subprocess.check_output(v, text=True).strip() for k, v in cmds.items()
        }
    except subprocess.CalledProcessError:
        return None


def emit_environment_description() -> dict[str, Any]:
    event: Event | None = emit_event(
        event="request.created.deployment",
        resource={
            "prefect.resource.id": f"deployment-request-{get_client_id()}",
            "prefect.resource.type": "deployment-request",
            "prefect.resource.description": "Deployment request",
        },
        payload={**(get_git_context() or {})},
    )

    assert isinstance(event, Event)

    return event.model_dump(exclude_none=True)
