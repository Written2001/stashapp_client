from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import pytest

from stashapp_client import StashClient
from stashapp_client.introspection import schema_document, schema_files
from stashapp_client.pagination import paginate, should_auto_paginate
from stashapp_client.registry import build_registry
from stashapp_client.runtime_bind import bind_registry


def test_build_registry_is_sorted_and_describes_arguments() -> None:
    schema = {
        "queryType": {"name": "Query"},
        "mutationType": None,
        "types": [
            {"name": "Query", "fields": [
                {"name": "findTags", "args": [{"name": "filter", "type": {"kind": "INPUT_OBJECT", "name": "FindFilterType"}}], "type": {"kind": "OBJECT", "name": "Tag"}},
                {"name": "version", "args": [], "type": {"kind": "SCALAR", "name": "String"}},
            ]},
        ],
    }

    registry = build_registry(schema)

    assert [item["name"] for item in registry["operations"]] == ["findTags", "version"]
    assert registry["operations"][0]["arguments"] == [{"name": "filter", "type": "FindFilterType"}]


def test_runtime_binding_dispatches_registry_operation() -> None:
    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"version": "0.31.1"}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]
    bind_registry(client, {"operations": [{"name": "version", "kind": "query", "arguments": [], "selection": "version"}]})

    assert client.version() == {"version": "0.31.1"}


def test_runtime_binding_renders_scalar_mutation_without_selection_set() -> None:
    queries: list[str] = []

    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            queries.append(kwargs["json"]["query"])

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"tagsDestroy": True}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]
    bind_registry(
        client,
        {
            "operations": [
                {
                    "name": "tagsDestroy",
                    "kind": "mutation",
                    "arguments": [{"name": "ids", "type": "[ID!]!"}],
                    "selection": "",
                }
            ]
        },
    )

    client.tagsDestroy(ids=["1"])

    assert "tagsDestroy(ids: $ids) }" in queries[0]
    assert "{  }" not in queries[0]


def test_runtime_binding_validates_generated_input_metadata_before_request() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.calls = 0

        def post(self, url: str, **kwargs: Any):
            self.calls += 1
            raise AssertionError("invalid input reached transport")

        def close(self) -> None:
            return None

    session = FakeSession()
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]
    bind_registry(
        client,
        {
            "input_fields": {
                "TagInput": {
                    "name": {"type": "String!", "required": True},
                    "description": {"type": "String", "required": False},
                }
            },
            "operations": [
                {
                    "name": "tagCreate",
                    "kind": "mutation",
                    "arguments": [{"name": "input", "type": "TagInput!"}],
                    "selection": "__typename",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="missing required"):
        client.tagCreate(input={})
    with pytest.raises(ValueError, match="missing required"):
        client.tagCreate(input={"name": None})

    assert session.calls == 0


def test_runtime_binding_rejects_null_non_null_list_element() -> None:
    client = StashClient("https://stash/graphql", "secret", session=None)
    bind_registry(
        client,
        {
            "input_fields": {
                "BatchInput": {
                    "ids": {"type": "[ID!]", "required": False},
                }
            },
            "operations": [
                {
                    "name": "batch",
                    "kind": "mutation",
                    "arguments": [{"name": "input", "type": "BatchInput!"}],
                    "selection": "__typename",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="must not be null"):
        client.batch(input={"ids": ["1", None]})

    client.close()


def test_generated_registry_is_packaged_as_client_data() -> None:
    registry = files("stashapp_client").joinpath("generated/operations_registry.json")

    assert registry.is_file()


def test_default_registry_exposes_generated_operation() -> None:
    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"findTags": {"tags": [{"id": "1", "name": "4k"}]}}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]

    result = client.findTags()

    assert list(result["name"]) == ["4k"]


def test_generated_find_operation_auto_paginates_all_results() -> None:
    calls: list[dict[str, Any]] = []

    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            calls.append(kwargs["json"]["variables"])
            page = kwargs["json"]["variables"]["filter"]["page"]
            rows = [{"id": str(index), "name": f"tag-{index}"} for index in range((page - 1) * 100, page * 100)]
            if page == 2:
                rows = [{"id": "100", "name": "tag-100"}]

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"findTags": {"tags": rows}}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]

    result = client.findTags(filter={"per_page": -1})

    assert len(result) == 101
    assert [variables["filter"]["page"] for variables in calls] == [1, 2]


def test_pagination_helper_stops_at_known_count() -> None:
    calls: list[tuple[int, int]] = []

    def fetch_page(page: int, page_size: int) -> list[int]:
        calls.append((page, page_size))
        return list(range((page - 1) * page_size, page * page_size))

    result = paginate(fetch_page, page_size=2, count=4)

    assert result == [0, 1, 2, 3]
    assert calls == [(1, 2), (2, 2)]
    assert should_auto_paginate({"per_page": -1})
    assert not should_auto_paginate({"per_page": 20})


def test_generated_operation_adds_requested_nested_field_to_document() -> None:
    queries: list[str] = []

    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            queries.append(kwargs["json"]["query"])

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"findPerformers": {"performers": [{"eye_color": "blue"}]}}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]

    result = client.findPerformers(field=["performers", "eye_color"])

    assert result == ["blue"]
    assert "performers" in queries[0]
    assert "eye_color" in queries[0]


def test_generated_operation_does_not_duplicate_nested_fragment_field() -> None:
    queries: list[str] = []

    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            queries.append(kwargs["json"]["query"])

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"findScenes": {"scenes": [{"studio": {"id": 1}}]}}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]

    result = client.findScenes(field=["scenes", "studio"])

    assert result.to_dict("records") == [{"id": 1}]
    assert "scenes {\n    ...Scene\n  }" in queries[0]
    assert "fragment Scene on Scene" in queries[0]
    assert "...Scene\n    studio" not in queries[0]


def test_generated_operation_rejects_unknown_requested_field() -> None:
    client = StashClient("https://stash/graphql", "secret", session=None)
    bind_registry(
        client,
        {
            "field_types": {
                "Result": {"items": "Item"},
                "Item": {"name": "String"},
            },
            "operations": [
                {
                    "name": "findItems",
                    "kind": "query",
                    "result_type": "Result",
                    "arguments": [],
                    "selection": "items { name }",
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="invalid response field path"):
        client.findItems(field=["items", "missing"])

    client.close()


def test_auto_pagination_does_not_repeat_non_tabular_result() -> None:
    calls: list[dict[str, Any]] = []

    class FakeSession:
        def post(self, url: str, **kwargs: Any):
            calls.append(kwargs["json"]["variables"])

            class Response:
                def raise_for_status(self) -> None:
                    return None

                def json(self) -> dict[str, Any]:
                    return {"data": {"findTags": {"count": 101}}}

            return Response()

        def close(self) -> None:
            return None

    client = StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]

    assert client.findTags(filter={"per_page": -1}, field="count") == 101
    assert len(calls) == 1


def test_schema_document_uses_sdl_as_source_and_records_provenance(tmp_path) -> None:
    schema_dir = tmp_path / "graphql" / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "schema.graphql").write_text(
        "type Query { version: String! }\n", encoding="utf-8"
    )

    document, provenance = schema_document(
        tmp_path, ref="v0.31.1", commit="abc123", package_version="0.1.0"
    )

    assert schema_files(tmp_path) == [Path("graphql/schema/schema.graphql")]
    assert document["data"]["__schema"]["queryType"]["name"] == "Query"
    assert provenance["ref"] == "v0.31.1"
    assert provenance["commit"] == "abc123"
    assert provenance["parser"] == "graphql-core"
