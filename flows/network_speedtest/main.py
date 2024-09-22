from typing import cast

import speedtest
from prefect import flow, task
from prefect.variables import Variable

EXPECTED_DOWNLOAD_SPEED = Variable.get("expected_download_speed", default=200)
EXPECTED_UPLOAD_SPEED = Variable.get("expected_upload_speed", default=100)


@task(timeout_seconds=60, retries=2)
def run_speed_test() -> tuple[float, float]:
    st = speedtest.Speedtest()

    # we can always use the task decorator to wrap the function inline
    download_speed = task(st.download)() / 1e6  # Convert to Mbps
    upload_speed = task(st.upload)() / 1e6  # Convert to Mbps

    return download_speed, upload_speed


@task
def check_threshold(upload_speed: float, download_speed: float) -> None:
    violations = []

    if download_speed < cast(int, EXPECTED_DOWNLOAD_SPEED):
        violations.append(
            f"Download speed {download_speed:.2f} Mbps below expected {EXPECTED_DOWNLOAD_SPEED} Mbps"
        )
    if upload_speed < cast(int, EXPECTED_UPLOAD_SPEED):
        violations.append(
            f"Upload speed {upload_speed:.2f} Mbps below expected {EXPECTED_UPLOAD_SPEED} Mbps"
        )

    if violations:
        raise ValueError(f"Network speed check failed:\n\n{'\n'.join(violations)}")


@flow
def monitor_network() -> None:
    state = check_threshold(*run_speed_test(), return_state=True)  # type: ignore
    print(f"Network monitoring finished in state: {state!r}")


if __name__ == "__main__":
    monitor_network.serve(cron="*/30 * * * *")
