"""Build and load deterministic operation registries from GraphQL schemas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_FRAGMENT_OVERRIDES = {
    "Scene": "id title",
    "Studio": "id name",
    "Performer": "id name gender",
    "Image": "id",
    "Gallery": "id title",
    "Tag": "id name",
    "Group": "id name",
    "ScrapedStudio": "stored_id name",
    "StashID": "endpoint stash_id",
    "Folder": "id path basename",
    "BasicFile": "id path basename",
    "ScrapedTag": "stored_id name description alias_list remote_site_id",
}


def load_registry(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate a generated registry JSON file."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("operations"), list):
        raise TypeError("registry must contain an operations list")
    return value


def build_registry(schema: dict[str, Any]) -> dict[str, Any]:
    """Create operation metadata from a GraphQL introspection schema."""
    types = {item["name"]: item for item in schema.get("types", []) if item.get("name")}
    operations: list[dict[str, Any]] = []
    for kind, root_key in (("query", "queryType"), ("mutation", "mutationType")):
        root = schema.get(root_key) or {}
        root_type = types.get(root.get("name"), {})
        for field in root_type.get("fields", []) or []:
            name = field["name"]
            result_type = _named_type(field.get("type", {}))
            operations.append(
                {
                    "name": name,
                    "kind": kind,
                    "result_type": result_type,
                    "default_field": _default_field(name, result_type, types),
                    "selection": _selection_for_type(result_type, types),
                    "arguments": [
                        {"name": arg["name"], "type": _type_string(arg["type"])}
                        for arg in field.get("args", [])
                    ],
                }
            )
    return {
        "schema": schema.get("description"),
        "operations": sorted(operations, key=lambda item: item["name"]),
    }


def save_registry(registry: dict[str, Any], path: str | Path) -> None:
    """Write a registry as deterministic, readable JSON."""
    Path(path).write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _named_type(type_ref: dict[str, Any]) -> str | None:
    current = type_ref
    while current:
        if current.get("name"):
            return current["name"]
        current = current.get("ofType") or {}
    return None


def _type_string(type_ref: dict[str, Any]) -> str:
    if type_ref.get("kind") == "NON_NULL":
        return f"{_type_string(type_ref['ofType'])}!"
    if type_ref.get("kind") == "LIST":
        return f"[{_type_string(type_ref['ofType'])}]"
    return type_ref.get("name", "Unknown")


def _default_field(
    operation: str, result_type: str | None, types: dict[str, dict[str, Any]]
) -> str | None:
    result_definition = types.get(result_type or "", {})
    fields = result_definition.get("fields", []) or []
    if any(field.get("name") == "count" for field in fields):
        for field in fields:
            if _contains_kind(field.get("type", {}), "LIST"):
                return field.get("name")
    if result_type and result_type.endswith("Result"):
        suffix = operation.removeprefix("find") or operation
        return suffix[:1].lower() + suffix[1:]
    return None


def _selection_for_type(type_name: str | None, types: dict[str, dict[str, Any]]) -> str:
    """Render a bounded selection for an operation result object."""
    if not type_name:
        return "__typename"
    definition = types.get(type_name, {})
    if definition.get("kind") in {"UNION", "INTERFACE"}:
        return "__typename"
    if definition.get("kind") != "OBJECT":
        return ""
    selections: list[str] = []
    for field in definition.get("fields", []) or []:
        if field.get("isDeprecated") or _has_required_arguments(field.get("args", [])):
            continue
        field_type = _named_type(field.get("type", {}))
        field_definition = types.get(field_type or "", {})
        if field_definition.get("kind") in {"OBJECT", "UNION", "INTERFACE"}:
            if type_name.endswith("ResultType"):
                nested = f"...{field_type}"
            else:
                nested = _compact_selection(field_type, types)
            if nested:
                selections.append(f"{field['name']} {{ {nested} }}")
        elif field_type:
            selections.append(field["name"])
    return " ".join(selections) or "__typename"


def _compact_selection(type_name: str | None, types: dict[str, dict[str, Any]]) -> str:
    """Select stable identity fields for nested objects without recursion."""
    definition = types.get(type_name or "", {})
    field_names = {field.get("name") for field in definition.get("fields", []) or []}
    override = DEFAULT_FRAGMENT_OVERRIDES.get(type_name or "")
    if override:
        return override
    preferred = ["id", "name", "title", "path", "basename", "stored_id", "endpoint", "stash_id"]
    selected = [name for name in preferred if name in field_names]
    return " ".join(selected) or "__typename"


def _has_required_arguments(arguments: list[dict[str, Any]] | None) -> bool:
    return any(argument.get("type", {}).get("kind") == "NON_NULL" for argument in arguments or [])


def _contains_kind(type_ref: dict[str, Any], kind: str) -> bool:
    current = type_ref
    while current:
        if current.get("kind") == kind:
            return True
        current = current.get("ofType") or {}
    return False
