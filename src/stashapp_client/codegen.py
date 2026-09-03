"""Render deterministic Python artifacts from schema-derived metadata."""

from __future__ import annotations

import json
from typing import Any

from .fragments import combine_fragments, get_dependent_fragments
from .registry import (
    DEFAULT_FRAGMENT_OVERRIDES,
    _compact_selection,
    _has_required_arguments,
    _named_type,
)


def render_inputs(schema: dict[str, Any]) -> str:
    """Render schema-derived input metadata and validation helpers."""
    specs = build_input_specs(schema)
    lines = [
        '"""Generated GraphQL input metadata and validation helpers."""',
        "",
        "from typing import Any",
        "",
        "from stashapp_client.input_validation import validate_input_value",
        "",
        f"INPUT_FIELDS = {specs!r}",
        "",
        "def validate_input(name: str, value: Any) -> Any:",
        "    \"\"\"Validate one generated GraphQL input object and return it.\"\"\"",
        "    return validate_input_value(name, value, INPUT_FIELDS)",
        "",
        "__all__ = [\"INPUT_FIELDS\", \"validate_input\"]",
        "",
    ]
    return "\n".join(lines)


def build_input_specs(schema: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    """Return input object fields with GraphQL type and required metadata."""
    specs: dict[str, dict[str, dict[str, Any]]] = {}
    for definition in schema.get("types", []):
        name = definition.get("name")
        if definition.get("kind") != "INPUT_OBJECT" or not name:
            continue
        specs[name] = {
            field["name"]: {
                "type": _type_string(field.get("type", {})),
                "required": field.get("type", {}).get("kind") == "NON_NULL",
            }
            for field in definition.get("inputFields", []) or []
            if field.get("name")
        }
    return dict(sorted(specs.items()))


def _type_string(type_ref: dict[str, Any]) -> str:
    if type_ref.get("kind") == "NON_NULL":
        return f"{_type_string(type_ref.get('ofType', {}))}!"
    if type_ref.get("kind") == "LIST":
        return f"[{_type_string(type_ref.get('ofType', {}))}]"
    return type_ref.get("name", "Unknown")


def render_fragments(schema: dict[str, Any]) -> str:
    """Render full root fragments with bounded nested object selections."""
    fragments = build_fragments(schema)
    lines = [
        '"""Generated schema-derived GraphQL fragments. Do not edit by hand."""',
        "",
        f"FRAGMENTS = {json.dumps(fragments, indent=2, sort_keys=True)}",
        "",
        "__all__ = [\"FRAGMENTS\"]",
        "",
    ]
    return "\n".join(lines)


def build_fragments(schema: dict[str, Any]) -> dict[str, str]:
    """Build full root fragment documents with bounded nested selections."""
    types = {item["name"]: item for item in schema.get("types", []) if item.get("name")}
    fragments: dict[str, str] = {}
    for name, definition in sorted(types.items()):
        if definition.get("kind") in {"UNION", "INTERFACE"} and not name.startswith("__"):
            possible = definition.get("possibleTypes", []) or []
            spreads = " ".join(
                f"...{item['name']}" for item in possible if item.get("name")
            )
            fragments[name] = f"fragment {name} on {name} {{ {spreads or '__typename'} }}"
            continue
        if definition.get("kind") != "OBJECT" or name.startswith("__"):
            continue
        selection = _root_selection(name, types)
        fragments[name] = f"fragment {name} on {name} {{ {selection} }}"

    return fragments


def attach_documents(registry: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Add fragment-backed GraphQL documents to a registry in place."""
    fragments = build_fragments(schema)
    registry["input_fields"] = build_input_specs(schema)
    registry["field_types"] = build_field_specs(schema)
    for operation in registry.get("operations", []):
        result_type = operation.get("result_type")
        if result_type not in fragments:
            continue
        operation["fragment_name"] = result_type
        operation["document"] = _operation_document(operation, fragments)
    return registry


def build_field_specs(schema: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """Return schema-derived field-to-named-type metadata for path validation."""
    specs: dict[str, dict[str, str | None]] = {}
    for definition in schema.get("types", []):
        name = definition.get("name")
        if not name:
            continue
        specs[name] = {
            field["name"]: _named_type(field.get("type", {}))
            for field in definition.get("fields", []) or []
            if field.get("name")
        }
    return dict(sorted(specs.items()))


def _operation_document(operation: dict[str, Any], fragments: dict[str, str]) -> str:
    kind = operation.get("kind", "query")
    name = operation["name"]
    arguments = operation.get("arguments", [])
    definitions = ", ".join(f"${item['name']}: {item['type']}" for item in arguments)
    passed = ", ".join(f"{item['name']}: ${item['name']}" for item in arguments)
    fragment_name = operation["fragment_name"]
    dependencies = get_dependent_fragments(fragment_name, fragments)
    fragment_definitions = combine_fragments(fragment_name, dependencies, fragments)
    variable_part = f"({definitions})" if definitions else ""
    passed_part = f"({passed})" if passed else ""
    document = (
        f"{kind} {name}{variable_part} {{ "
        f"{name}{passed_part} {{ ...{fragment_name} }} }}"
    )
    return f"{document}\n{fragment_definitions}"


def _root_selection(type_name: str, types: dict[str, dict[str, Any]]) -> str:
    definition = types.get(type_name, {})
    selections: list[str] = []
    for field in definition.get("fields", []) or []:
        if field.get("isDeprecated") or _has_required_arguments(field.get("args", [])):
            continue
        field_type = _named_type(field.get("type", {}))
        field_definition = types.get(field_type or "", {})
        if field_definition.get("kind") in {"OBJECT", "UNION", "INTERFACE"}:
            if type_name.endswith("ResultType"):
                nested = f"...{field_type}"
            elif field_type in DEFAULT_FRAGMENT_OVERRIDES or _reenters(field_type or "", type_name, types):
                nested = _compact_selection(field_type, types)
            else:
                nested = f"...{field_type}"
            selections.append(f"{field['name']} {{ {nested} }}")
        elif field_type:
            selections.append(field["name"])
    return " ".join(selections) or "__typename"


def _reenters(type_name: str, target: str, types: dict[str, dict[str, Any]]) -> bool:
    """Return whether following object fields from a type can reach the target."""
    pending = [type_name]
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        definition = types.get(current, {})
        for field in definition.get("fields", []) or []:
            nested = _named_type(field.get("type", {}))
            if types.get(nested or "", {}).get("kind") == "OBJECT":
                pending.append(nested)
    return False
