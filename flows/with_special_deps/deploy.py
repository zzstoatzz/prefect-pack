import emoji
from prefect import flow


@flow
def emoji_flow(message: str = "Hello, World!"):
    return emoji.emojize(message)


if __name__ == "__main__":
    """from repo root:
    python flows/with_special_deps/deploy.py
    """
    flow.from_source(
        source="https://github.com/zzstoatzz/prefect-pack.git",
        entrypoint="flows/with_special_deps/main.py:emoji_flow",
    ).deploy(name="emoji-flow", work_pool_name="docker-work")
