from __future__ import annotations

import pytest

from stashapp_client.criteria import between, includes, is_null, not_null
from stashapp_client.errors import StashResponseError
from stashapp_client.filters import (
    find_filter,
    gallery_filter,
    group_filter,
    image_filter,
    marker_filter,
    performer_filter,
    scene_filter,
    studio_filter,
    tag_filter,
)
from stashapp_client.generated.inputs import INPUT_FIELDS


def test_criteria_match_graphql_input_shape() -> None:
    assert includes(182, depth=-1, excludes=[183]) == {
        "value": 182,
        "modifier": "INCLUDES",
        "depth": -1,
        "excludes": [183],
    }
    assert between(1, 10) == {"value": 1, "value2": 10, "modifier": "BETWEEN"}
    assert is_null() == {"value": True, "modifier": "IS_NULL"}
    assert not_null() == {"value": False, "modifier": "IS_NULL"}


def test_filter_builder_validates_and_composes_values() -> None:
    result = scene_filter(tags=includes(182), organized=is_null(False))
    assert result["tags"]["modifier"] == "INCLUDES"
    assert result["organized"]["value"] is False

    with pytest.raises(StashResponseError, match="unknown"):
        scene_filter(not_a_schema_field=1)


def test_filter_builder_supports_explicit_non_strict_mode_and_alias() -> None:
    assert scene_filter(strict=False, newer_field=1)["newer_field"] == 1
    assert studio_filter(stash_id={"value": "abc"}) == {
        "stash_id_endpoint": {"value": "abc"}
    }


@pytest.mark.parametrize(
    ("helper", "input_type"),
    [
        (find_filter, "FindFilterType"),
        (scene_filter, "SceneFilterType"),
        (image_filter, "ImageFilterType"),
        (gallery_filter, "GalleryFilterType"),
        (performer_filter, "PerformerFilterType"),
        (studio_filter, "StudioFilterType"),
        (tag_filter, "TagFilterType"),
        (group_filter, "GroupFilterType"),
        (marker_filter, "SceneMarkerFilterType"),
    ],
)
def test_filter_helpers_accept_all_generated_schema_fields(helper, input_type) -> None:
    for field in INPUT_FIELDS[input_type]:
        assert field in helper(**{field: object()})


def test_performer_filter_accepts_hair_color() -> None:
    assert performer_filter(hair_color={"value": "brown"}) == {
        "hair_color": {"value": "brown"}
    }
