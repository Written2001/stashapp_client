"""Reusable pagination helpers for Stash list operations."""

from collections.abc import Callable
from typing import Any

import pandas as pd

DEFAULT_PAGE_SIZE = 100


def should_auto_paginate(filter_value: Any, *, response: str = "data") -> bool:
    """Return whether a filter requests all pages in data mode."""
    return response == "data" and isinstance(filter_value, dict) and filter_value.get("per_page") == -1


def paginate(
    fetch_page: Callable[[int, int], Any],
    *,
    start_page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    count: int | None = None,
) -> Any:
    """Fetch and merge pages until the known count or a short page is reached."""
    if start_page < 1:
        raise ValueError("start_page must be at least 1")
    if page_size < 1:
        raise ValueError("page_size must be at least 1")
    pages: list[Any] = []
    page = start_page
    fetched = 0
    while True:
        page_result = fetch_page(page, page_size)
        pages.append(page_result)
        page_length = _result_length(page_result)
        fetched += page_length
        if count is not None and fetched >= count:
            break
        if page_length < page_size:
            break
        page += 1
    return _merge_pages(pages)


def _result_length(result: Any) -> int:
    if isinstance(result, (pd.DataFrame, list, tuple)):
        return len(result)
    return 0


def _merge_pages(pages: list[Any]) -> Any:
    if not pages:
        return []
    if all(isinstance(page, pd.DataFrame) for page in pages):
        return pd.concat(pages, ignore_index=True)
    if all(isinstance(page, list) for page in pages):
        return [item for page in pages for item in page]
    return pages[0]
