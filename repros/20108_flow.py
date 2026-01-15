"""Test flow for issue #20108 - intentionally fails so we can test force reschedule."""

from prefect import flow


@flow(log_prints=True)
def test_20108_flow(should_fail: bool = True):
    if should_fail:
        raise ValueError("Intentional failure for issue #20108 test")
    print("Flow completed successfully!")


if __name__ == "__main__":
    test_20108_flow()
