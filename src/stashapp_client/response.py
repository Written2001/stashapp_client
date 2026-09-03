"""GraphQL response extraction and normalization."""

from typing import Any

import pandas as pd

from .errors import GraphQLError, StashResponseError


def extract_response(
    envelope: dict[str, Any],
    *,
    response: str = "data",
    field: str | list[str] | None = None,
) -> Any:
    """Extract a GraphQL envelope as data, an object, or raw JSON.

    In data mode, list-of-dictionary results become DataFrames and GraphQL
    errors raise ``GraphQLError``. Object mode preserves ``data`` alongside
    non-data metadata, while raw mode returns the envelope unchanged.
    """
    if response not in {"data", "object", "raw"}:
        raise ValueError("response must be 'data', 'object', or 'raw'")
    if not isinstance(envelope, dict) or "data" not in envelope and "errors" not in envelope:
        raise StashResponseError("GraphQL response must contain data or errors")
    errors = envelope.get("errors")
    if errors and response == "data":
        raise GraphQLError(errors, envelope.get("data"))
    if response == "raw":
        if field is not None:
            raise ValueError("field cannot be used with raw response mode")
        return envelope
    data = envelope.get("data")
    if field is not None:
        path = [field] if isinstance(field, str) else field
        for key in path:
            if isinstance(data, list):
                if not all(item is None or isinstance(item, dict) and key in item for item in data):
                    raise StashResponseError(f"response field not found: {'.'.join(path)}")
                data = [item[key] if item is not None else None for item in data]
                continue
            if not isinstance(data, dict) or key not in data:
                raise StashResponseError(f"response field not found: {'.'.join(path)}")
            data = data[key]
    if response == "object":
        meta = {key: value for key, value in envelope.items() if key != "data"}
        meta.setdefault("errors", errors)
        return {"data": data, "meta": meta}
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return pd.DataFrame(data)
    return data


def flatten_column(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Expand dictionary values in a DataFrame column into prefixed columns."""
    if column not in frame.columns:
        raise KeyError(column)
    values = frame[column].map(lambda value: value if isinstance(value, dict) else {})
    flattened = pd.json_normalize(values)
    flattened.columns = [f"{column}.{name}" for name in flattened.columns]
    flattened.index = frame.index
    return pd.concat([frame.drop(columns=[column]), flattened], axis=1)


def explode_column(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """Explode a list-valued DataFrame column while preserving empty rows."""
    if column not in frame.columns:
        raise KeyError(column)
    return frame.explode(column, ignore_index=True)
