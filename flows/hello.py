import platform
import subprocess
import sys

from prefect import flow


@flow(log_prints=True)
def print_info():
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    prefect_version = subprocess.check_output(["prefect", "version"]).decode().strip()
    print(f"Prefect version: {prefect_version}")


if __name__ == "__main__":
    # prefect will find the above flow and execute it
    # but you can serve the flow locally for testing
    print_info.serve(name="print-info-test")
