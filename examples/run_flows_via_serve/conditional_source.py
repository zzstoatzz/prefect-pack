import os
from pathlib import Path

from prefect import flow
from prefect.runner.storage import GitRepository


@flow
def f():
    pass


if __name__ == "__main__":
    repo_url = os.getenv("GITLAB_REPO")

    source = (
        GitRepository(url=repo_url) if repo_url else str(Path(__file__).parent.parent)
    )

    f.from_source(
        source=source,
        entrypoint="examples/run_flows_via_serve/conditional_source.py:f",
    ).serve()
