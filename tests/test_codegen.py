from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from stashapp_client import cli
from stashapp_client.codegen import (
    attach_documents,
    render_fragments,
    render_inputs,
)
from stashapp_client.fragments import combine_fragments, get_dependent_fragments
from stashapp_client.schema_diff import compare_schemas, format_report, has_changes


def test_generated_fragments_keep_full_root_selection() -> None:
    schema = {
        "types": [
            {
                "name": "Scene",
                "kind": "OBJECT",
                "fields": [
                    {"name": "id", "type": {"kind": "SCALAR", "name": "ID"}},
                    {"name": "title", "type": {"kind": "SCALAR", "name": "String"}},
                    {
                        "name": "studio",
                        "type": {"kind": "OBJECT", "name": "Studio"},
                    },
                ],
            },
            {
                "name": "Studio",
                "kind": "OBJECT",
                "fields": [
                    {"name": "id", "type": {"kind": "SCALAR", "name": "ID"}},
                    {"name": "name", "type": {"kind": "SCALAR", "name": "String"}},
                ],
            },
            {"name": "String", "kind": "SCALAR"},
        ]
    }

    rendered = render_fragments(schema)

    assert '"Scene": "fragment Scene on Scene { id title studio { ...Studio } }"' in rendered
    assert '"Studio": "fragment Studio on Studio { id name }"' in rendered


def test_object_operations_use_root_fragment_and_definitions() -> None:
    schema = {
        "queryType": {"name": "Query"},
        "mutationType": None,
        "types": [
            {
                "name": "Query",
                "kind": "OBJECT",
                "fields": [
                    {
                        "name": "findScene",
                        "args": [],
                        "type": {"kind": "OBJECT", "name": "Scene"},
                    }
                ],
            },
            {
                "name": "Scene",
                "kind": "OBJECT",
                "fields": [{"name": "id", "type": {"kind": "SCALAR", "name": "ID"}}],
            },
        ],
    }
    from stashapp_client.registry import build_registry

    registry = attach_documents(build_registry(schema), schema)
    operation = registry["operations"][0]

    assert operation["fragment_name"] == "Scene"
    assert "findScene { ...Scene }" in operation["document"]
    assert "fragment Scene on Scene { id }" in operation["document"]


def test_fragment_generation_handles_abstract_and_recursive_types() -> None:
    schema = {
        "types": [
            {
                "name": "Package",
                "kind": "OBJECT",
                "fields": [{"name": "requires", "type": {"kind": "OBJECT", "name": "Package"}}],
            },
            {
                "name": "VisualFile",
                "kind": "UNION",
                "possibleTypes": [{"name": "VideoFile"}],
            },
            {"name": "VideoFile", "kind": "OBJECT", "fields": []},
        ]
    }

    rendered = render_fragments(schema)

    assert '"VisualFile": "fragment VisualFile on VisualFile { ...VideoFile }"' in rendered
    assert '"Package": "fragment Package on Package { requires { __typename } }"' in rendered


def test_tag_result_uses_full_tag_fragment() -> None:
    schema = {
        "types": [
            {
                "name": "FindTagsResultType",
                "kind": "OBJECT",
                "fields": [
                    {
                        "name": "tags",
                        "type": {"kind": "LIST", "ofType": {"kind": "OBJECT", "name": "Tag"}},
                    }
                ],
            },
            {
                "name": "Tag",
                "kind": "OBJECT",
                "fields": [
                    {"name": "id", "type": {"kind": "SCALAR", "name": "ID"}},
                    {"name": "description", "type": {"kind": "SCALAR", "name": "String"}},
                    {
                        "name": "fingerprint",
                        "args": [
                            {
                                "name": "type",
                                "type": {"kind": "NON_NULL", "ofType": {"kind": "SCALAR", "name": "String"}},
                            }
                        ],
                        "type": {"kind": "SCALAR", "name": "String"},
                    },
                    {"name": "parents", "type": {"kind": "OBJECT", "name": "Tag"}},
                ],
            },
        ],
    }

    rendered = render_fragments(schema)

    assert '"FindTagsResultType": "fragment FindTagsResultType on FindTagsResultType { tags { ...Tag } }"' in rendered
    assert 'fragment Tag on Tag { id description parents { id } }' in rendered
    assert "fingerprint" not in rendered


def test_schema_diff_reports_operation_and_type_changes() -> None:
    baseline = {
        "queryType": {"name": "Query"},
        "types": [
            {"name": "Query", "fields": [{"name": "version", "args": [], "type": {"name": "String"}}]},
            {"name": "Tag", "kind": "OBJECT", "fields": [{"name": "name", "type": {"name": "String"}}]},
        ],
    }
    current = {
        "queryType": {"name": "Query"},
        "types": [
            {"name": "Query", "fields": [{"name": "version", "args": [], "type": {"name": "Int"}}, {"name": "health", "args": [], "type": {"name": "Boolean"}}]},
            {"name": "Tag", "kind": "OBJECT", "fields": [{"name": "name", "type": {"name": "String"}}, {"name": "id", "type": {"name": "ID"}}]},
        ],
    }

    report = compare_schemas(baseline, current)

    assert report["added_operations"] == ["query.health"]
    assert report["changed_operations"] == ["query.version"]
    assert report["changed_types"] == ["Query", "Tag"]
    assert has_changes(report)
    assert "added_operations: query.health" in format_report(report)


def test_schema_diff_reports_abstract_and_metadata_changes() -> None:
    baseline = {
        "types": [
            {
                "name": "Node",
                "kind": "INTERFACE",
                "possibleTypes": [{"name": "Tag"}],
                "fields": [{"name": "id", "type": {"name": "ID"}}],
            }
        ]
    }
    current = {
        "types": [
            {
                "name": "Node",
                "kind": "INTERFACE",
                "possibleTypes": [{"name": "Tag"}, {"name": "Scene"}],
                "fields": [{"name": "id", "type": {"name": "ID"}, "isDeprecated": True}],
            }
        ]
    }

    report = compare_schemas(baseline, current)

    assert report["changed_types"] == ["Node"]


def test_generated_input_metadata_validates_required_and_unknown_fields() -> None:
    schema = {
        "types": [
            {
                "name": "TagInput",
                "kind": "INPUT_OBJECT",
                "inputFields": [
                    {"name": "name", "type": {"kind": "NON_NULL", "ofType": {"name": "String"}}},
                    {"name": "description", "type": {"kind": "SCALAR", "name": "String"}},
                ],
            }
        ]
    }

    rendered = render_inputs(schema)

    namespace: dict[str, Any] = {}
    exec(rendered, namespace)  # noqa: S102
    assert namespace["validate_input"]("TagInput", {"name": "4k"}) == {"name": "4k"}
    with pytest.raises(ValueError, match="missing required"):
        namespace["validate_input"]("TagInput", {})
    with pytest.raises(ValueError, match="unknown fields"):
        namespace["validate_input"]("TagInput", {"name": "4k", "extra": True})
    with pytest.raises(ValueError, match="missing required"):
        namespace["validate_input"]("TagInput", {"name": None})


def test_fragments_resolve_transitive_dependencies() -> None:
    fragments = {
        "Scene": {"fragment_string": "fragment Scene on Scene { tags { ...Tag } }"},
        "Tag": {"fragment_string": "fragment Tag on Tag { id name }"},
    }

    dependencies = get_dependent_fragments("Scene", fragments)

    assert dependencies == ["Tag"]
    assert combine_fragments("Scene", dependencies, fragments).splitlines() == [
        "fragment Tag on Tag { id name }",
        "fragment Scene on Scene { tags { ...Tag } }",
    ]


def test_build_ops_cli_writes_all_artifacts(tmp_path: Path) -> None:
    schema_path = tmp_path / "input.json"
    output_args = [
        "--out-schema",
        str(tmp_path / "schema.json"),
        "--out-registry",
        str(tmp_path / "operations_registry.json"),
        "--out-fragments",
        str(tmp_path / "fragments.py"),
        "--out-inputs",
        str(tmp_path / "inputs.py"),
    ]
    schema_path.write_text(
        json.dumps({"data": {"__schema": {"queryType": None, "mutationType": None, "types": []}}}),
        encoding="utf-8",
    )

    cli.main(["build-ops", "--schema", str(schema_path), *output_args])

    assert (tmp_path / "schema.json").exists()
    assert (tmp_path / "operations_registry.json").exists()
    assert (tmp_path / "fragments.py").exists()
    assert (tmp_path / "inputs.py").exists()


def test_build_ops_cli_attaches_documents_and_input_metadata(tmp_path: Path) -> None:
    schema_path = tmp_path / "input.json"
    schema_path.write_text(
        json.dumps(
            {
                "data": {
                    "__schema": {
                        "queryType": {"name": "Query"},
                        "mutationType": None,
                        "types": [
                            {
                                "name": "Query",
                                "kind": "OBJECT",
                                "fields": [
                                    {
                                        "name": "version",
                                        "args": [],
                                        "type": {"kind": "OBJECT", "name": "Version"},
                                    }
                                ],
                            },
                            {
                                "name": "Version",
                                "kind": "OBJECT",
                                "fields": [{"name": "value", "type": {"kind": "SCALAR", "name": "String"}}],
                            },
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    cli.main(
        [
            "build-ops",
            "--schema",
            str(schema_path),
            "--out-schema",
            str(tmp_path / "schema.json"),
            "--out-registry",
            str(tmp_path / "registry.json"),
            "--out-fragments",
            str(tmp_path / "fragments.py"),
            "--out-inputs",
            str(tmp_path / "inputs.py"),
        ]
    )

    registry = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
    assert registry["input_fields"] == {}
    assert "document" in registry["operations"][0]