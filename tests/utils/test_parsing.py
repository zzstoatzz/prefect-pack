from prefect_pack import parse_as
from pydantic import BaseModel


def test_parsing():
    class Fruit(BaseModel):
        name: str
        color: str

    assert parse_as(Fruit, {"name": "apple", "color": "red"}) == Fruit(
        name="apple", color="red"
    )
