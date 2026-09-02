"""Bind registry-described GraphQL operations to a client."""

from __future__ import annotations

import copy
from typing import Any

from graphql import parse, print_ast
from graphql.language.ast import (
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    NameNode,
    SelectionSetNode,
)

from .input_validation import validate_input_value
from .pagination import paginate, should_auto_paginate
from .registry import load_registry


def bind_registry(client: Any, registry: dict[str, Any]) -> None:
    """Install operation methods described by a registry on a client instance."""
    client._registry_input_fields = registry.get("input_fields", {})
    client._registry_field_types = registry.get("field_types", {})
    for operation in registry["operations"]:
        setattr(client, operation["name"], _operation_method(client, operation))


def load_and_bind(client: Any, path: str) -> None:
    bind_registry(client, load_registry(path))


def _operation_method(client: Any, operation: dict[str, Any]):
    def call(*, response: str = "data", field: str | list[str] | None = None, **kwargs: Any) -> Any:
        declared = {argument["name"] for argument in operation.get("arguments", [])}
        unknown = set(kwargs) - declared
        if unknown:
            names = ", ".join(sorted(unknown))
            raise TypeError(f"unexpected arguments for {operation['name']}: {names}")
        variables = {key: value for key, value in kwargs.items()}
        _validate_inputs(operation, variables, client._registry_input_fields)
        document = operation.get("document") or _document(operation)
        selected_field = field
        requested_path = [field] if isinstance(field, str) else field
        if response == "data" and (selected_field is not None or operation.get("default_field")):
            path = [selected_field] if isinstance(selected_field, str) else selected_field
            selected_field = [operation["name"], *(path or [operation["default_field"]])]
            if requested_path:
                _validate_field_path(operation, requested_path, client._registry_field_types)
                document = _document_with_field(document, requested_path)
        filter_value = variables.get("filter")
        if should_auto_paginate(filter_value, response=response):
            page = int(filter_value.get("page", 1))
            def fetch_page(page_number: int, page_size: int) -> Any:
                page_filter = {**filter_value, "page": page_number, "per_page": page_size}
                page_variables = {**variables, "filter": page_filter}
                return client.execute(
                    document, page_variables, response=response, field=selected_field
                )

            return paginate(fetch_page, start_page=page)
        return client.execute(document, variables, response=response, field=selected_field)

    call.__name__ = operation["name"]
    call.__doc__ = f"Call GraphQL {operation.get('kind', 'query')} operation {operation['name']}."
    return call


def _validate_inputs(
    operation: dict[str, Any], variables: dict[str, Any], input_fields: dict[str, Any]
) -> None:
    if not input_fields:
        return
    for argument in operation.get("arguments", []):
        name = argument["name"]
        if name not in variables:
            continue
        input_name = _input_name(argument.get("type", ""), input_fields)
        if input_name:
            validate_input_value(
                input_name,
                variables[name],
                input_fields,
                name,
                argument.get("type", ""),
            )


def _validate_field_path(
    operation: dict[str, Any], path: list[str], field_types: dict[str, Any]
) -> None:
    if not field_types:
        return
    current_type = operation.get("result_type")
    for field in path:
        fields = field_types.get(current_type or "")
        if not fields or field not in fields:
            joined = ".".join(path)
            raise ValueError(f"invalid response field path for {operation['name']}: {joined}")
        current_type = fields[field]


def _input_name(type_string: str, input_fields: dict[str, Any]) -> str | None:
    candidate = type_string.replace("!", "").replace("[", "").replace("]", "")
    return candidate if candidate in input_fields else None


def _document(operation: dict[str, Any]) -> str:
    kind = operation.get("kind", "query")
    name = operation["name"]
    arguments = operation.get("arguments", [])
    definitions = ", ".join(f"${item['name']}: {item['type']}" for item in arguments)
    passed = ", ".join(f"{item['name']}: ${item['name']}" for item in arguments)
    selection = operation.get("selection", "__typename")
    variable_part = f"({definitions})" if definitions else ""
    passed_part = f"({passed})" if passed else ""
    selection_part = f" {{ {selection} }}" if selection else ""
    return f"{kind} {name}{variable_part} {{ {name}{passed_part}{selection_part} }}"


def _document_with_field(document: str, path: list[str]) -> str:
    """Add a requested response path to the relevant generated selection."""
    if not path:
        return document
    parsed = parse(document)
    fragments = {
        definition.name.value: definition
        for definition in parsed.definitions
        if isinstance(definition, FragmentDefinitionNode)
    }
    definitions = []
    for definition in parsed.definitions:
        if isinstance(definition, FragmentDefinitionNode):
            definition = fragments.get(definition.name.value, definition)
            updated = _augment_fragment(definition, path, fragments, set())
            definitions.append(updated)
        else:
            definitions.append(definition)
    return print_ast(parsed.__class__(definitions=tuple(definitions)))


def _augment_fragment(
    fragment: FragmentDefinitionNode,
    path: list[str],
    fragments: dict[str, FragmentDefinitionNode],
    visited: set[str],
) -> FragmentDefinitionNode:
    name = fragment.name.value
    if name in visited:
        return fragment
    visited.add(name)
    updated_selection = _augment_selection_set(
        fragment.selection_set, path, fragments, visited, add_leaf=False
    )
    updated = copy.copy(fragment)
    updated.selection_set = updated_selection
    fragments[name] = updated
    return updated


def _augment_selection_set(
    selection_set: SelectionSetNode,
    path: list[str],
    fragments: dict[str, FragmentDefinitionNode],
    visited: set[str],
    *,
    add_leaf: bool,
) -> SelectionSetNode:
    target = path[0]
    selections = list(selection_set.selections)
    changed = False
    found = False
    for index, selection in enumerate(selections):
        if isinstance(selection, FieldNode) and selection.name.value == target:
            found = True
            if len(path) > 1 and selection.selection_set is not None:
                child = _augment_selection_set(
                    selection.selection_set,
                    path[1:],
                    fragments,
                    visited,
                    add_leaf=True,
                )
                if child is not selection.selection_set:
                    updated = copy.copy(selection)
                    updated.selection_set = child
                    selections[index] = updated
                    changed = True
        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment is not None and fragment.name.value not in visited:
                _augment_fragment(fragment, path, fragments, visited)
    if add_leaf and not found:
        selections.append(FieldNode(name=NameNode(value=target)))
        changed = True
    if changed:
        updated_set = copy.copy(selection_set)
        updated_set.selections = tuple(selections)
        return updated_set
    return selection_set
