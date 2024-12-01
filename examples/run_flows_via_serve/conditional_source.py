import os
from pathlib import Path

from prefect import flow
from prefect.runner.storage import GitRepository


@flow
def f():
    pass


if __name__ == "__main__":
    repo = os.getenv("GIT_REPO")

    source = (
        GitRepository(url=f"https://github.com/{repo}.git")
        if repo
        else str(Path(__file__).parent.parent.parent)
    )

    print(f"Using source: {source}")

    f.from_source(
        source=source,
        entrypoint="examples/run_flows_via_serve/conditional_source.py:f",
    ).serve()
