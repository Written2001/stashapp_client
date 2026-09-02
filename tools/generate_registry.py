"""Generate operation metadata from pinned Stash SDL or a schema snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path

from stashapp_client.codegen import (
    attach_documents,
    render_fragments,
    render_inputs,
)
from stashapp_client.introspection import load_schema, save_schema, schema_document
from stashapp_client.registry import build_registry, save_registry


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-root", type=Path, help="pinned Stash checkout containing SDL")
    source.add_argument("--schema", type=Path, help="existing introspection snapshot")
    parser.add_argument("--schema-output", type=Path, help="write the derived introspection snapshot")
    parser.add_argument("--registry-output", type=Path, required=True)
    parser.add_argument("--fragments-output", type=Path)
    parser.add_argument("--inputs-output", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--commit")
    args = parser.parse_args()

    if args.source_root:
        document, provenance = schema_document(args.source_root, ref=args.ref, commit=args.commit)
        schema = document["data"]["__schema"]
        if args.schema_output:
            save_schema(document, args.schema_output)
    else:
        schema = load_schema(args.schema)
        provenance = {"source": "introspection-snapshot", "path": str(args.schema)}

    registry = build_registry(schema)
    registry["provenance"] = provenance
    attach_documents(registry, schema)
    save_registry(registry, args.registry_output)
    if args.fragments_output:
        args.fragments_output.write_text(render_fragments(schema), encoding="utf-8")
    if args.inputs_output:
        args.inputs_output.write_text(render_inputs(schema), encoding="utf-8")


if __name__ == "__main__":
    main()
