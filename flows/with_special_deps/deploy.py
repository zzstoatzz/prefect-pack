from pathlib import Path

import emoji
from prefect import flow
from prefect.docker import DockerImage

docker_image = DockerImage(
    name="zzstoatzz/prefect-pack",
    tag="with-special-deps",
    dockerfile=str(Path(__file__).parent / "Dockerfile"),
)


@flow
def emoji_flow(message: str = "Hello, World!"):
    return emoji.emojize(message)


if __name__ == "__main__":
    """test it out from repo root (using dockerhub as registry):
    ```bash
    python flows/with_special_deps/deploy.py
    prefect deployment run "emoji-flow/emoji-deployment"
    prefect worker start --pool docker-work
    ```
    """
    flow.from_source(
        source="https://github.com/zzstoatzz/prefect-pack.git",
        entrypoint="flows/with_special_deps/deploy.py:emoji_flow",
    ).deploy(
        name="emoji-deployment",
        work_pool_name="docker-work",
        image=docker_image,
        push=True,
    )
