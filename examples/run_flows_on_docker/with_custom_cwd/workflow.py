from pathlib import Path

import pandas as pd
from prefect import flow
from prefect.docker import DockerImage


@flow
def the_work_is_mysterious_and_important():
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    print(df.head())


if __name__ == "__main__":
    the_work_is_mysterious_and_important.deploy(
        name="the-work-is-mysterious-and-important",
        work_pool_name="docker-work",
        image=DockerImage(
            name="zzstoatzz/prefect-pack",
            tag="the-work-is-mysterious-and-important",
            dockerfile=str(Path(__file__).parent / "Dockerfile"),
        ),
    )
