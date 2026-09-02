"""Compose schema-derived GraphQL fragments deterministically."""

from __future__ import annotations

import re
from typing import Any

_SPREAD_PATTERN = re.compile(r"\.\.\.([_A-Za-z][_0-9A-Za-z]*)")


def get_dependent_fragments(name: str, fragments: dict[str, Any]) -> list[str]:
    """Return transitive fragment dependencies in stable dependency order."""
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(current: str) -> None:
        if current in visited or current in visiting:
            return
        visiting.add(current)
        for dependency in _dependencies(fragments.get(current)):
            if dependency in fragments:
                visit(dependency)
                if dependency not in ordered:
                    ordered.append(dependency)
        visiting.remove(current)
        visited.add(current)

    visit(name)
    return ordered


def combine_fragments(name: str, dependencies: list[str], fragments: dict[str, Any]) -> str:
    """Combine dependencies and a root fragment into one GraphQL document."""
    names: list[str] = []
    for fragment_name in [*dependencies, name]:
        if fragment_name in fragments and fragment_name not in names:
            names.append(fragment_name)
    return "\n".join(_fragment_text(fragments[fragment_name]) for fragment_name in names)


def _dependencies(fragment: Any) -> list[str]:
    if isinstance(fragment, dict):
        explicit = fragment.get("frag_objects")
        if isinstance(explicit, list):
            return [name for name in explicit if isinstance(name, str)]
        fragment = fragment.get("fragment_string", "")
    if not isinstance(fragment, str):
        return []
    return _SPREAD_PATTERN.findall(fragment)


def _fragment_text(fragment: Any) -> str:
    if isinstance(fragment, dict):
        fragment = fragment.get("fragment_string", "")
    return fragment if isinstance(fragment, str) else ""