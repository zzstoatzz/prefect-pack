"""
basic demo using pandas and prefect
"""

import pandas as pd
from prefect import flow


@flow(log_prints=True)
def main():
    df = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
        }
    )
    print(df)


if __name__ == "__main__":
    main()
