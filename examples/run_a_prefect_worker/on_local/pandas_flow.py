from prefect import flow


@flow(log_prints=True)
def uses_pandas():
    import pandas as pd

    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})

    assert df.shape == (3, 2)

    print(df)


if __name__ == "__main__":
    uses_pandas()
