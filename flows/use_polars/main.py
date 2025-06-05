"""
basic demo using polars and prefect
"""

import polars as pl
from prefect import flow


@flow(log_prints=True)
def main():
    df = pl.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        }
    )
    print(df)


if __name__ == "__main__":
    main()
