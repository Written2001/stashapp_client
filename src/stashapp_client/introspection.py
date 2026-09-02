"""SDL-derived schema snapshots and optional live introspection loading.

The normal generation path starts with a pinned Stash checkout and compiles its
SDL into an introspection-shaped document. The live query is retained for
diagnostics and explicit synchronization workflows only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from graphql import build_ast_schema, parse
from graphql.utilities import get_introspection_query, introspection_from_schema

SCHEMA_QUERY = get_introspection_query(descriptions=True)

SCHEMA_PATTERNS = ("graphql/schema/types/*.graphql", "graphql/schema/*.graphql")
SCHEMA_SOURCE_URL = "https://github.com/stashapp/stash"


def schema_files(source_root: str | Path, patterns: Iterable[str] = SCHEMA_PATTERNS) -> list[Path]:
    """Return the sorted SDL files used to build a Stash schema snapshot."""
    root = Path(source_root)
    if not root.is_dir():
        raise ValueError(f"source root does not exist: {root}")
    files = {
        path.relative_to(root)
        for pattern in patterns
        for path in root.glob(pattern)
        if path.is_file()
    }
    if not files:
        raise ValueError("no Stash GraphQL schema files matched the configured patterns")
    return sorted(files)


def schema_document(
    source_root: str | Path,
    *,
    ref: str | None = None,
    commit: str | None = None,
    package_version: str | None = None,
    artifact: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build an introspection document and provenance from a pinned Stash checkout."""
    root = Path(source_root)
    files = schema_files(root)
    definitions = "\n\n".join((root / path).read_text(encoding="utf-8") for path in files)
    schema = build_ast_schema(parse(definitions), assume_valid=False)
    provenance: dict[str, Any] = {
        "source": SCHEMA_SOURCE_URL,
        "ref": ref,
        "patterns": list(SCHEMA_PATTERNS),
        "files": [path.as_posix() for path in files],
        "fingerprints": {
            path.as_posix(): hashlib.md5(
                (root / path).read_bytes(), usedforsecurity=False
            ).hexdigest()
            for path in files
        },
        "parser": "graphql-core",
    }
    if commit is not None:
        provenance["commit"] = commit
    if package_version is not None:
        provenance["stashapi_version"] = package_version
    if artifact is not None:
        provenance["artifact"] = artifact
    return {"data": introspection_from_schema(schema)}, provenance


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load a GraphQL introspection envelope or its ``__schema`` object."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if "data" in value:
        value = value["data"]
    if "__schema" in value:
        value = value["__schema"]
    if not isinstance(value, dict) or "types" not in value:
        raise ValueError("schema must contain a GraphQL __schema object")
    return value


def save_schema(schema: dict[str, Any], path: str | Path) -> None:
    """Write a normalized, stable JSON schema snapshot."""
    Path(path).write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def introspect_schema(client: Any) -> dict[str, Any]:
    """Fetch and return the server's introspection schema."""
    envelope = client.execute(SCHEMA_QUERY, response="raw")
    try:
        schema = envelope["data"]["__schema"]
    except (KeyError, TypeError) as exc:
        raise ValueError("introspection response did not contain __schema") from exc
    if not isinstance(schema, dict):
        raise TypeError("introspection __schema must be an object")
    return schema
