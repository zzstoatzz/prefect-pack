from prefect import flow


@flow
def uses_pandas():
    import pandas

    print(pandas.__version__)


if __name__ == "__main__":
    uses_pandas()
