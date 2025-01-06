from prefect import flow


@flow(log_prints=True)
def uses_pandas():
    import pandas as pd  # type: ignore

    df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})  # type: ignore

    assert df.shape == (3, 2)  # type: ignore

    print(df)  # type: ignore


if __name__ == "__main__":
    uses_pandas()
