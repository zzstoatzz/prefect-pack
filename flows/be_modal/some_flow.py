import pandas as pd
from prefect import flow, task


@task
def print_result_row(row: pd.Index):
    print(row)


@flow(log_prints=True)
def hello_world():
    df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    df["z"] = df["x"] + df["y"]
    return print_result_row.map(df.itertuples())


if __name__ == "__main__":
    hello_world()
