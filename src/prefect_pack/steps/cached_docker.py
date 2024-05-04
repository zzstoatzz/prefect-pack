from functools import lru_cache

from prefect.logging.loggers import get_logger
from prefect_docker.deployments.steps import (
    BuildDockerImageResult,
    PushDockerImageResult,
    build_docker_image,
    push_docker_image,
)

logger = get_logger("prefect_pack.steps.cached_docker")


@lru_cache
def build_image(
    image_name: str,
    dockerfile: str,
    tag: str | None = None,
    additional_tags: list[str] | None = None,
    **build_kwargs,
) -> BuildDockerImageResult:
    """Cached version of `prefect_docker.deployments.steps.build_docker_image`."""
    return build_docker_image(
        image_name=image_name,
        dockerfile=dockerfile,
        tag=tag,
        additional_tags=additional_tags,
        **build_kwargs,
    )


@lru_cache
def push_image(
    image_name: str,
    tag: str,
    credentials: dict[str, str] | None = None,
    additional_tags: list[str] | None = None,
    **push_kwargs,
) -> PushDockerImageResult:
    """Cached version of `prefect_docker.deployments.steps.push_docker_image`."""
    return push_docker_image(
        image_name=image_name,
        tag=tag,
        credentials=credentials,
        additional_tags=additional_tags,
        **push_kwargs,
    )
