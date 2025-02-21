import pandas as pd  # type: ignore
from prefect import flow


@flow(log_prints=True)
def load_titanic_dataset():
    titanic = pd.read_csv(  # type: ignore
        "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
    )
    print(titanic.head())
