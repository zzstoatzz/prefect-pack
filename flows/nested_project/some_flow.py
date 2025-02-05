from prefect import flow


@flow
def some_flow():
    print("Hello, world!")
