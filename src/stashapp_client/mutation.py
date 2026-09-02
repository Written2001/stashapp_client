"""Reviewable, dry-run-first mutation plans."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class MutationEntry:
    index: int
    input: dict[str, Any]
    omitted: tuple[str, ...] = ()


@dataclass
class MutationPlan:
    entries: list[MutationEntry]
    operation: str | None = None

    def execute(
        self,
        mutate: Callable[..., Any],
        *,
        dry_run: bool = True,
        on_error: str = "stop",
        argument: str = "input",
    ) -> dict[str, Any]:
        """Execute one mutation per plan entry, or return a dry-run preview."""
        if on_error not in {"stop", "continue"}:
            raise ValueError("on_error must be 'stop' or 'continue'")
        results: list[dict[str, Any]] = []
        for entry in self.entries:
            result: dict[str, Any] = {"index": entry.index, "input": entry.input}
            if dry_run:
                result["status"] = "planned"
            else:
                try:
                    payload = entry.input.get(argument, entry.input)
                    result["value"] = mutate(**{argument: payload})
                    result["status"] = "succeeded"
                except Exception as exc:  # noqa: BLE001
                    result["status"] = "failed"
                    result["error"] = exc
                    results.append(result)
                    if on_error == "stop":
                        break
                    continue
            results.append(result)
        return {"operation": self.operation, "dry_run": dry_run, "results": results}


def prepare_mutations(
    data: Iterable[Any],
    build_input: Callable[[Any, int], dict[str, Any]],
    *,
    na: str = "omit",
    null: str = "omit",
    operation: str | None = None,
) -> MutationPlan:
    """Build normalized mutation inputs without making network requests."""
    if na not in {"omit", "error"} or null not in {"omit", "error"}:
        raise ValueError("na and null must be 'omit' or 'error'")
    entries: list[MutationEntry] = []
    for index, row in enumerate(_rows(data), start=1):
        built = build_input(row, index)
        if not isinstance(built, dict):
            raise TypeError("build_input must return a dictionary")
        normalized, omitted = _normalize(built, na=na, null=null, path="")
        entries.append(MutationEntry(index, normalized, tuple(omitted)))
    return MutationPlan(entries, operation)


def _rows(data: Iterable[Any]) -> Iterable[Any]:
    if isinstance(data, pd.DataFrame):
        return (row for _, row in data.iterrows())
    return data


def _normalize(value: Any, *, na: str, null: str, path: str) -> tuple[Any, list[str]]:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        omitted: list[str] = []
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if child is None:
                if null == "error":
                    raise ValueError(f"mutation input contains NULL at {child_path}")
                omitted.append(child_path)
                continue
            if _is_na(child):
                if na == "error":
                    raise ValueError(f"mutation input contains NA at {child_path}")
                omitted.append(child_path)
                continue
            normalized, child_omitted = _normalize(child, na=na, null=null, path=child_path)
            result[key] = normalized
            omitted.extend(child_omitted)
        return result, omitted
    if isinstance(value, list):
        normalized_items: list[Any] = []
        omitted: list[str] = []
        for item in value:
            if item is None:
                if null == "error":
                    raise ValueError(f"mutation input contains NULL at {path}")
                continue
            if _is_na(item):
                if na == "error":
                    raise ValueError(f"mutation input contains NA at {path}")
                continue
            normalized, child_omitted = _normalize(item, na=na, null=null, path=path)
            normalized_items.append(normalized)
            omitted.extend(child_omitted)
        return normalized_items, omitted
    return value, []


def _is_na(value: Any) -> bool:
    if value is None:
        return False
    try:
        result = pd.isna(value)
        return isinstance(result, bool) and result
    except (TypeError, ValueError):
        return False
