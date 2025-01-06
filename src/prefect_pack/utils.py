from collections.abc import Callable
from typing import Any, Literal, TypeVar, get_origin

from pydantic import TypeAdapter

T = TypeVar("T")

_adapter_cache: dict[type[Any], TypeAdapter[Any]] = {}


def parse_as(
    type_: type[T],
    data: Any,
    mode: Literal["python", "json", "strings"] = "python",
) -> T:
    """Parse a given data structure as a Pydantic model via `TypeAdapter`.

    Read more about `TypeAdapter` [here](https://docs.pydantic.dev/latest/concepts/type_adapter/).

    Args:
        type_: The type to parse the data as.
        data: The data to be parsed.
        mode: The mode to use for parsing, either `python`, `json`, or `strings`.
            Defaults to `python`, where `data` should be a Python object (e.g. `dict`).

    Returns:
        The parsed `data` as the given `type_`.

    Example:
        ```python
        from pydantic import BaseModel
        from prefect_pack import parse_as

        class GitHubIssue(BaseModel):
            title: str

        issue = parse_as(GitHubIssue, {"title": "Test Issue"})
        print(issue.title)
        # => "Test Issue"
        ```
    """
    adapter = _adapter_cache.get(type_)
    if adapter is None:
        adapter = TypeAdapter(type_)
        _adapter_cache[type_] = adapter

    parser: Callable[[Any], T] = getattr(adapter, f"validate_{mode}")

    if get_origin(type_) is list and isinstance(data, dict):
        values: dict[Any, Any] = data
        data = next(iter(values.values()))

    return parser(data)
