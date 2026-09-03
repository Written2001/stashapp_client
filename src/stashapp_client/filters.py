"""Schema-shaped builders for common Stash filter input objects."""

from typing import Any

from .errors import StashResponseError
from .generated.inputs import INPUT_FIELDS

_FILTER_TYPES = {
    "find": "FindFilterType",
    "scene": "SceneFilterType",
    "image": "ImageFilterType",
    "gallery": "GalleryFilterType",
    "performer": "PerformerFilterType",
    "studio": "StudioFilterType",
    "tag": "TagFilterType",
    "group": "GroupFilterType",
    "marker": "SceneMarkerFilterType",
}
_FIELDS = {
    kind: set(INPUT_FIELDS[input_name]) for kind, input_name in _FILTER_TYPES.items()
}
_FIELDS["performer"].add("stash_id")
_FIELDS["studio"].add("stash_id")
_FIELDS["tag"].add("stash_id")


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
