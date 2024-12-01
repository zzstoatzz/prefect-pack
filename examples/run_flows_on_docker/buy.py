import subprocess
from pathlib import Path

from prefect import flow
from prefect.docker import DockerImage


@flow(log_prints=True)
def buy():
    print("Buying securities")


if __name__ == "__main__":
    try:
        subprocess.check_call(
            [
                "prefect",
                "work-pool",
                "create",
                "my-work-pool",
                "--type",
                "docker",
                "--overwrite",
            ]
        )

        buy.deploy(
            name="my-deployment",
            work_pool_name="my-work-pool",
            image=DockerImage(
                name="zzstoatzz/prefect-pack",
                tag="buy",
                dockerfile=str(Path(__file__).parent / "Dockerfile"),
            ),
            push=False,
            job_variables={"image": "zzstoatzz/prefect-pack:buy"},
        )

        subprocess.check_call(["prefect", "deployment", "run", "buy/my-deployment"])

        subprocess.check_call(
            [
                "prefect",
                "worker",
                "start",
                "--pool",
                "my-work-pool",
                "--run-once",
            ]
        )
    finally:
        subprocess.check_call(
            ["prefect", "--no-prompt", "work-pool", "delete", "my-work-pool"]
        )
