import os
import subprocess
import time
from typing import Any

from prefect.events import Event, emit_event


def get_client_id() -> str:
    """hostname and pid of the client"""
    return f"{os.uname().nodename}-{os.getpid()}-{int(time.time())}"


def get_git_context() -> dict[str, str] | None:
    """Retrieve information about the current git repository.

    Returns:
        A dictionary containing information about the current git repository,
        or None if the current directory is not a git repository.
    """
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


def emit_environment_description(**kwargs) -> dict[str, Any] | None:
    """Gather and emit information about the origin of a deployment request.

    Args:
        **kwargs: Arbitrary keyword arguments to include in the event payload.

    Returns:
        A dictionary containing the event payload, if an event was emitted.
    """
    event: Event | None = emit_event(
        event="deployment-request.created",
        resource={
            "prefect.resource.id": f"deployment-request-{get_client_id()}",
            "prefect.resource.description": "Someone requested a deployment",
        },
        payload=dict(**kwargs | (get_git_context() or {})),
    )

    return event.model_dump(exclude_none=True) if event else {}
