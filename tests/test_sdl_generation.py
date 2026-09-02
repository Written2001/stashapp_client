from __future__ import annotations

from pathlib import Path

from stashapp_client.introspection import schema_document
from stashapp_client.registry import build_registry


def test_sdl_document_feeds_registry_without_live_introspection(tmp_path: Path) -> None:
    schema_dir = tmp_path / "graphql" / "schema"
    schema_dir.mkdir(parents=True)
    (schema_dir / "schema.graphql").write_text(
        """
        type Query { version: String! findTags(filter: FindFilterType): TagResult! }
        input FindFilterType { q: String }
        type TagResult { tags: [Tag!]! count: Int! }
        type Tag { id: ID! name: String! }
        """,
        encoding="utf-8",
    )

    document, _ = schema_document(tmp_path, ref="v0.31.1", commit="abc")
    registry = build_registry(document["data"]["__schema"])

    operations = {item["name"]: item for item in registry["operations"]}
    assert operations["findTags"]["arguments"] == [{"name": "filter", "type": "FindFilterType"}]
    assert operations["findTags"]["result_type"] == "TagResult"
    assert operations["findTags"]["default_field"] == "tags"
