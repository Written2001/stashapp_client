"""Schema-shaped builders for common Stash filter input objects."""

from typing import Any

from .errors import StashResponseError

_FIELDS = {
    "find": {"q", "page", "per_page", "sort", "direction"},
    "scene": {"id", "title", "date", "details", "organized", "rating100", "duration", "tags", "performers", "studios", "performers_filter", "studios_filter", "AND", "OR", "NOT"},
    "image": {"id", "path", "rating100", "organized", "date", "galleries", "studios", "tags", "performers", "AND", "OR", "NOT"},
    "gallery": {"id", "title", "date", "organized", "rating100", "has_chapters", "performers", "studios", "tags", "AND", "OR", "NOT"},
    "performer": {"id", "name", "gender", "country", "rating100", "image_count", "stash_id", "stash_id_endpoint", "AND", "OR", "NOT"},
    "studio": {"id", "name", "url", "favorite", "scene_count", "image_count", "stash_id", "stash_id_endpoint", "AND", "OR", "NOT"},
    "tag": {"id", "name", "favorite", "scene_count", "image_count", "stash_id", "AND", "OR", "NOT"},
    "group": {"id", "name", "rating100", "scene_count", "performers", "studios", "tags", "AND", "OR", "NOT"},
    "marker": {"id", "title", "seconds", "duration", "scene_id", "tags", "AND", "OR", "NOT"},
}


def _build(kind: str, values: dict[str, Any], *, strict: bool) -> dict[str, Any]:
    unknown = set(values) - _FIELDS[kind]
    if strict and unknown:
        names = ", ".join(sorted(unknown))
        raise StashResponseError(f"unknown fields for {kind}_filter: {names}")
    result = dict(values)
    if kind == "studio" and "stash_id" in result:
        result["stash_id_endpoint"] = result.pop("stash_id")
    return result


def find_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build pagination and sorting values for ``find*`` operations.

    Accepted fields are ``q``, ``page``, ``per_page``, ``sort``, and
    ``direction``. Set ``strict=False`` to pass through additional fields.
    """
    return _build("find", values, strict=strict)


def scene_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a scene filter from schema-shaped keyword arguments."""
    return _build("scene", values, strict=strict)


def image_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build an image filter from schema-shaped keyword arguments."""
    return _build("image", values, strict=strict)


def gallery_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a gallery filter from schema-shaped keyword arguments."""
    return _build("gallery", values, strict=strict)


def performer_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a performer filter from schema-shaped keyword arguments."""
    return _build("performer", values, strict=strict)


def studio_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a studio filter and normalize ``stash_id`` to its endpoint field."""
    return _build("studio", values, strict=strict)


def tag_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a tag filter from schema-shaped keyword arguments."""
    return _build("tag", values, strict=strict)


def group_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a group filter from schema-shaped keyword arguments."""
    return _build("group", values, strict=strict)


def marker_filter(*, strict: bool = True, **values: Any) -> dict[str, Any]:
    """Build a marker filter from schema-shaped keyword arguments."""
    return _build("marker", values, strict=strict)
