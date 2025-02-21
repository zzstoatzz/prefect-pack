"""Create a flow with two schedules that run at the same time."""

from prefect import flow
from prefect.schedules import Cron


@flow(flow_run_name="saying hello to {name}!")
def say_hello(name: str):
    print(f"Hello, {name}!")


if __name__ == "__main__":
    say_hello.serve(
        schedules=[
            Cron("*/5 * * * *", parameters={"name": "Bari"}, slug="bari-schedule"),
            Cron("*/5 * * * *", parameters={"name": "Bart"}, slug="bart-schedule"),
        ]
    )
