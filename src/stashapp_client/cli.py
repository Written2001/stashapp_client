"""Command-line entry point for schema and operation generation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .client import StashClient
from .codegen import attach_documents, render_fragments, render_inputs
from .introspection import introspect_schema, load_schema, save_schema
from .registry import build_registry, save_registry
from .schema_diff import compare_schemas, format_report, has_changes, report_json


def _path_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out-schema", type=Path, default=Path("schema.json"))
    parser.add_argument("--out-registry", type=Path, default=Path("operations_registry.json"))
    parser.add_argument("--out-fragments", type=Path, default=Path("fragments.py"))
    parser.add_argument("--out-inputs", type=Path, default=Path("inputs.py"))


def _write_artifacts(schema: dict[str, Any], provenance: dict[str, Any], args: Any) -> None:
    save_schema({"data": {"__schema": schema}}, args.out_schema)
    registry = attach_documents(build_registry(schema), schema)
    registry["provenance"] = provenance
    save_registry(registry, args.out_registry)
    args.out_fragments.write_text(render_fragments(schema), encoding="utf-8")
    args.out_inputs.write_text(render_inputs(schema), encoding="utf-8")


def _verify_value(value: str) -> bool | str:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stashapp-client")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-ops", help="build artifacts from a schema snapshot")
    build.add_argument("--schema", type=Path, required=True)
    _path_options(build)

    sync = commands.add_parser("sync-schema", help="introspect a live server and build artifacts")
    sync.add_argument("--credentials-file", type=Path, required=True)
    sync.add_argument("--verify", type=_verify_value, default=True)
    sync.add_argument("--timeout", type=float, default=30)
    _path_options(sync)

    diff = commands.add_parser("diff-schema", help="compare two schema snapshots")
    diff.add_argument("--base", type=Path, required=True)
    diff.add_argument("--current", type=Path, required=True)
    diff.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the schema generation or schema comparison command-line interface."""
    args = _parser().parse_args(argv)
    if args.command == "build-ops":
        _write_artifacts(
            load_schema(args.schema),
            {"source": "introspection-snapshot", "path": str(args.schema)},
            args,
        )
        return
    if args.command == "diff-schema":
        report = compare_schemas(load_schema(args.base), load_schema(args.current))
        print(report_json(report) if args.as_json else format_report(report))
        if has_changes(report):
            raise SystemExit(1)
        return

    client = StashClient.from_credentials_file(
        args.credentials_file, verify=args.verify, timeout=args.timeout
    )
    try:
        schema = introspect_schema(client)
    finally:
        client.close()
    _write_artifacts(
        schema,
        {"source": "live-introspection", "path": str(args.credentials_file)},
        args,
    )


if __name__ == "__main__":
    main()
