"""Build a GraphQL introspection snapshot from a pinned Stash SDL checkout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stashapp_client.introspection import schema_document


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance-output", type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--commit")
    parser.add_argument("--package-version")
    parser.add_argument("--artifact")
    args = parser.parse_args()
    document, provenance = schema_document(
        args.source_root,
        ref=args.ref,
        commit=args.commit,
        package_version=args.package_version,
        artifact=args.artifact,
    )
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.provenance_output:
        args.provenance_output.write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()