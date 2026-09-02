"""Small builders for Stash GraphQL filter criteria."""

from typing import Any


def gql_criterion(modifier: str, value: Any = None, **extra: Any) -> dict[str, Any]:
    criterion: dict[str, Any] = {"modifier": modifier}
    if value is not None:
        criterion["value"] = value
    criterion.update(extra)
    return criterion


def equals(value: Any) -> dict[str, Any]:
    return gql_criterion("EQUALS", value)


def not_equals(value: Any) -> dict[str, Any]:
    return gql_criterion("NOT_EQUALS", value)


def includes(value: Any, *, depth: int | None = None, excludes: Any = None) -> dict[str, Any]:
    return _hierarchy("INCLUDES", value, depth=depth, excludes=excludes)


def includes_all(value: Any, *, depth: int | None = None, excludes: Any = None) -> dict[str, Any]:
    return _hierarchy("INCLUDES_ALL", value, depth=depth, excludes=excludes)


def excludes(value: Any, *, depth: int | None = None) -> dict[str, Any]:
    return _hierarchy("EXCLUDES", value, depth=depth)


def between(start: Any, end: Any) -> dict[str, Any]:
    return {"value": start, "value2": end, "modifier": "BETWEEN"}


def greater_than(value: Any) -> dict[str, Any]:
    return gql_criterion("GREATER_THAN", value)


def less_than(value: Any) -> dict[str, Any]:
    return gql_criterion("LESS_THAN", value)


def matches_regex(value: str) -> dict[str, Any]:
    return gql_criterion("MATCHES_REGEX", value)


def not_matches_regex(value: str) -> dict[str, Any]:
    return gql_criterion("NOT_MATCHES_REGEX", value)


def is_null(value: bool = True) -> dict[str, Any]:
    return gql_criterion("IS_NULL", value)


def not_null() -> dict[str, Any]:
    return is_null(False)


def stash_id(endpoint: str, value: str) -> dict[str, Any]:
    return {"endpoint": endpoint, "stash_id": value}


def stash_ids(endpoint: str, values: list[str]) -> dict[str, Any]:
    return {"endpoint": endpoint, "stash_ids": values}


def _hierarchy(modifier: str, value: Any, **kwargs: Any) -> dict[str, Any]:
    criterion = gql_criterion(modifier, value)
    criterion.update({key: value for key, value in kwargs.items() if value is not None})
    return criterion
