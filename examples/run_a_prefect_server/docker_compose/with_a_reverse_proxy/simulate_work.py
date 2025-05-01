### /// script
# requires-python = ">=3.10"
# dependencies = ["prefect"]
# ///

from prefect import flow, task


@flow
def simulated_work():
    task(lambda x: print(f"hello {x}")).map(range(10)).wait()


if __name__ == "__main__":
    simulated_work()
