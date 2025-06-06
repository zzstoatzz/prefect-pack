"""
basic demo using polars and prefect
"""

import polars as pl
from prefect import flow, task


@task
def make_one_dataframe():
    df = pl.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        }
    )
    print(df)


@task
def modify_one_dataframe(df: pl.DataFrame):
    df = df.with_columns(pl.col("age") + 1)
    print(df)


@task
def save_one_dataframe(df: pl.DataFrame):
    df.write_csv("one_dataframe.csv")


@flow(log_prints=True)
def main():
    df = make_one_dataframe()
    df = modify_one_dataframe(df)
    save_one_dataframe(df)


if __name__ == "__main__":
    main()
