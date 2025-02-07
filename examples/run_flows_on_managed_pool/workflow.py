import pandas as pd
from prefect import flow


@flow(log_prints=True)
def load_titanic_dataset():
    titanic = pd.read_csv(
        "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv"
    )
    print(titanic.head())
