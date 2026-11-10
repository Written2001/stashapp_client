"""Validation for schema-derived GraphQL input objects."""

import json
from typing import Any


def validate_input_value(
    name: str,
    value: Any,
    input_fields: dict[str, Any],
    path: str | None = None,
    type_string: str | None = None,
) -> Any:
    """Validate a GraphQL input against generated type and field metadata.

    The validator checks unknown fields, required fields, nested input objects,
    and list nullability before a request is sent.
    """
    if name not in input_fields:
        raise KeyError(f"unknown GraphQL input object: {name}")
    location = path or name
    if type_string:
        _validate_list_nullability(value, type_string, location)
    if isinstance(value, list):
        for index, item in enumerate(value):
            if item is not None:
                _validate_input(name, item, input_fields, f"{location}[{index}]")
        return value
    _validate_input(name, value, input_fields, location)
    return value


def _validate_input(name: str, value: Any, input_fields: dict[str, Any], path: str) -> None:
    if isinstance(value, list):
        raise TypeError(f"{path} must be a dictionary")
    if not isinstance(value, dict):
        raise TypeError(f"{path} must be a dictionary")
    fields = input_fields[name]
    unknown = set(value) - set(fields)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"unknown fields for {name}: {names}")
    missing = [
        field
        for field, spec in fields.items()
        if spec["required"] and (field not in value or value[field] is None)
    ]
    if missing:
        names = ", ".join(sorted(missing))
        raise ValueError(f"missing required fields for {name}: {names}")
    for field, spec in fields.items():
        if field not in value or value[field] is None:
            continue
        field_path = f"{path}.{field}"
        _validate_json_value(value[field], field_path)
        _validate_list_nullability(value[field], spec["type"], field_path)
        nested = _input_name(spec["type"], input_fields)
        if nested:
            _validate_nested(nested, value[field], input_fields, field_path)


def _validate_nested(
    name: str, value: Any, input_fields: dict[str, Any], path: str
) -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            if item is not None:
                _validate_input(name, item, input_fields, f"{path}[{index}]")
        return
    _validate_input(name, value, input_fields, path)


def _validate_list_nullability(value: Any, type_string: str, path: str) -> None:
    if not type_string.startswith("["):
        return
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{path} must be a list")
    closing = type_string.rfind("]")
    item_type = type_string[1:closing]
    item_non_null = item_type.endswith("!")
    item_type = item_type.removesuffix("!")
    for index, item in enumerate(value):
        if item is None and item_non_null:
            raise ValueError(f"{path}[{index}] must not be null")
        if item is not None:
            _validate_list_nullability(item, item_type, f"{path}[{index}]")


def _validate_json_value(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains a non-string object key")
            _validate_json_value(item, f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{path} must be JSON-serializable") from exc


def _input_name(type_string: str, input_fields: dict[str, Any]) -> str | None:
    candidate = type_string.replace("!", "").replace("[", "").replace("]", "")
    return candidate if candidate in input_fields else None
