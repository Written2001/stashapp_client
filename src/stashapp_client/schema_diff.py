"""Compatibility reports for GraphQL schema snapshots."""

from __future__ import annotations

import json
from typing import Any


def compare_schemas(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic additions, removals, and signature changes."""
    baseline_types = _type_map(baseline)
    current_types = _type_map(current)
    baseline_operations = _operation_map(baseline)
    current_operations = _operation_map(current)
    return {
        "added_operations": sorted(set(current_operations) - set(baseline_operations)),
        "removed_operations": sorted(set(baseline_operations) - set(current_operations)),
        "changed_operations": _changed(baseline_operations, current_operations),
        "added_types": sorted(set(current_types) - set(baseline_types)),
        "removed_types": sorted(set(baseline_types) - set(current_types)),
        "changed_types": _changed(baseline_types, current_types),
    }


def has_changes(report: dict[str, Any]) -> bool:
    """Return whether a compatibility report contains any differences."""
    return any(bool(value) for value in report.values())


def format_report(report: dict[str, Any]) -> str:
    """Render a concise human-readable compatibility report."""
    if not has_changes(report):
        return "No schema changes detected."
    lines: list[str] = []
    for key in (
        "added_operations",
        "removed_operations",
        "changed_operations",
        "added_types",
        "removed_types",
        "changed_types",
    ):
        values = report[key]
        if values:
            lines.append(f"{key}: {', '.join(values)}")
    return "\n".join(lines)


def _type_map(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        item["name"]: _type_signature(item)
        for item in schema.get("types", [])
        if item.get("name") and not item["name"].startswith("__")
    }


def _operation_map(schema: dict[str, Any]) -> dict[str, Any]:
    operations: dict[str, Any] = {}
    for kind, root_key in (("query", "queryType"), ("mutation", "mutationType")):
        root_name = (schema.get(root_key) or {}).get("name")
        root = next((item for item in schema.get("types", []) if item.get("name") == root_name), {})
        for field in root.get("fields", []) or []:
            name = f"{kind}.{field['name']}"
            operations[name] = {
                "type": _type_string(field.get("type", {})),
                "arguments": sorted(
                    (arg["name"], _type_string(arg.get("type", {})))
                    for arg in field.get("args", []) or []
                ),
            }
    return operations


def _type_signature(definition: dict[str, Any]) -> dict[str, Any]:
    fields = {
        field["name"]: {
            "type": _type_string(field.get("type", {})),
            "arguments": sorted(
                (arg["name"], _type_string(arg.get("type", {})))
                for arg in field.get("args", []) or []
            ),
            "deprecated": field.get("isDeprecated", False),
            "deprecation_reason": field.get("deprecationReason"),
        }
        for field in definition.get("fields", []) or []
        if field.get("name")
    }
    inputs = {
        field["name"]: {
            "type": _type_string(field.get("type", {})),
            "default": field.get("defaultValue"),
        }
        for field in definition.get("inputFields", []) or []
        if field.get("name")
    }
    enum_values = sorted(
        (
            value["name"],
            value.get("isDeprecated", False),
            value.get("deprecationReason"),
        )
        for value in definition.get("enumValues", []) or []
        if value.get("name")
    )
    possible_types = sorted(
        item["name"]
        for item in definition.get("possibleTypes", []) or []
        if item.get("name")
    )
    return {
        "kind": definition.get("kind"),
        "fields": fields,
        "input_fields": inputs,
        "enum_values": enum_values,
        "possible_types": possible_types,
    }


def _changed(baseline: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return sorted(name for name in set(baseline) & set(current) if baseline[name] != current[name])


def _type_string(type_ref: dict[str, Any]) -> str:
    kind = type_ref.get("kind")
    if kind == "NON_NULL":
        return f"{_type_string(type_ref.get('ofType', {}))}!"
    if kind == "LIST":
        return f"[{_type_string(type_ref.get('ofType', {}))}]"
    return type_ref.get("name", "Unknown")


def report_json(report: dict[str, Any]) -> str:
    """Serialize a report for machine-readable CLI output."""
    return json.dumps(report, indent=2, sort_keys=True)