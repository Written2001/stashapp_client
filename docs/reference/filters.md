# Filters and criteria

Filter helpers return ordinary dictionaries shaped for Stash GraphQL input
objects. Pass them to the matching `*_filter` operation argument.

## Filter builders

The available builders and their complete set of accepted fields are:

| Builder | Allowed fields |
| --- | --- |
| `find_filter` | `direction`, `page`, `per_page`, `q`, `sort` |
| `scene_filter` | `AND`, `NOT`, `OR`, `audio_codec`, `bitrate`, `captions`, `checksum`, `code`, `created_at`, `custom_fields`, `date`, `details`, `director`, `duplicated`, `duration`, `file_count`, `files_filter`, `framerate`, `galleries`, `galleries_filter`, `groups`, `groups_filter`, `has_markers`, `id`, `interactive`, `interactive_speed`, `is_missing`, `last_played_at`, `markers_filter`, `movies`, `movies_filter`, `o_counter`, `organized`, `orientation`, `oshash`, `path`, `performer_age`, `performer_count`, `performer_favorite`, `performer_tags`, `performers`, `performers_filter`, `phash`, `phash_distance`, `play_count`, `play_duration`, `rating100`, `resolution`, `resume_time`, `stash_id_count`, `stash_id_endpoint`, `stash_ids_endpoint`, `studios`, `studios_filter`, `tag_count`, `tags`, `tags_filter`, `title`, `updated_at`, `url`, `video_codec` |
| `image_filter` | `AND`, `NOT`, `OR`, `checksum`, `code`, `created_at`, `custom_fields`, `date`, `details`, `file_count`, `files_filter`, `galleries`, `galleries_filter`, `id`, `is_missing`, `o_counter`, `organized`, `orientation`, `path`, `performer_age`, `performer_count`, `performer_favorite`, `performer_tags`, `performers`, `performers_filter`, `phash_distance`, `photographer`, `rating100`, `resolution`, `studios`, `studios_filter`, `tag_count`, `tags`, `tags_filter`, `title`, `updated_at`, `url` |
| `gallery_filter` | `AND`, `NOT`, `OR`, `average_resolution`, `checksum`, `code`, `created_at`, `custom_fields`, `date`, `details`, `file_count`, `files_filter`, `folders_filter`, `has_chapters`, `id`, `image_count`, `images_filter`, `is_missing`, `is_zip`, `organized`, `parent_folder`, `path`, `performer_age`, `performer_count`, `performer_favorite`, `performer_tags`, `performers`, `performers_filter`, `photographer`, `rating100`, `scenes`, `scenes_filter`, `studios`, `studios_filter`, `tag_count`, `tags`, `tags_filter`, `title`, `updated_at`, `url` |
| `performer_filter` | `AND`, `NOT`, `OR`, `age`, `aliases`, `birth_year`, `birthdate`, `career_end`, `career_length`, `career_start`, `circumcised`, `country`, `created_at`, `custom_fields`, `death_date`, `death_year`, `details`, `disambiguation`, `ethnicity`, `eye_color`, `fake_tits`, `filter_favorites`, `galleries_filter`, `gallery_count`, `gender`, `groups`, `hair_color`, `height_cm`, `ignore_auto_tag`, `image_count`, `images_filter`, `is_missing`, `marker_count`, `markers_filter`, `measurements`, `name`, `o_counter`, `penis_length`, `performers`, `piercings`, `play_count`, `rating100`, `scene_count`, `scenes_filter`, `stash_id_endpoint`, `stash_ids_endpoint`, `studios`, `tag_count`, `tags`, `tags_filter`, `tattoos`, `updated_at`, `url`, `weight`, and the compatibility alias `stash_id` |
| `studio_filter` | `AND`, `NOT`, `OR`, `aliases`, `child_count`, `created_at`, `custom_fields`, `details`, `favorite`, `galleries_filter`, `gallery_count`, `group_count`, `groups_filter`, `ignore_auto_tag`, `image_count`, `images_filter`, `is_missing`, `name`, `organized`, `parents`, `rating100`, `scene_count`, `scenes_filter`, `stash_id_endpoint`, `stash_ids_endpoint`, `tag_count`, `tags`, `updated_at`, `url`, and the compatibility alias `stash_id` |
| `tag_filter` | `AND`, `NOT`, `OR`, `aliases`, `child_count`, `children`, `created_at`, `custom_fields`, `description`, `favorite`, `galleries_filter`, `gallery_count`, `group_count`, `groups_filter`, `ignore_auto_tag`, `image_count`, `images_filter`, `is_missing`, `marker_count`, `markers_filter`, `movie_count`, `name`, `parent_count`, `parents`, `performer_count`, `performers_filter`, `scene_count`, `scenes_filter`, `sort_name`, `stash_id_endpoint`, `stash_ids_endpoint`, `studio_count`, `studios_filter`, `updated_at`, and the compatibility alias `stash_id` |
| `group_filter` | `AND`, `NOT`, `OR`, `containing_group_count`, `containing_groups`, `created_at`, `custom_fields`, `date`, `director`, `duration`, `is_missing`, `name`, `o_counter`, `performers`, `rating100`, `scene_count`, `scenes_filter`, `studios`, `studios_filter`, `sub_group_count`, `sub_groups`, `synopsis`, `tag_count`, `tags`, `updated_at`, `url` |
| `marker_filter` | `created_at`, `duration`, `performers`, `scene_created_at`, `scene_date`, `scene_filter`, `scene_tags`, `scene_updated_at`, `scenes`, `tags`, `updated_at` |

All builders accept `AND`, `OR`, and `NOT` for boolean composition where those
fields are present in the table. They reject
unknown keyword fields by default with `strict=True`:

```python
from stashapp_client import scene_filter

scene_filter(title={"modifier": "INCLUDES", "value": "demo"})
# scene_filter(unknown=True) raises StashResponseError
scene_filter(unknown=True, strict=False)  # pass through a newer server field
```

The helpers are convenience builders, not a replacement for schema validation.
When targeting a different Stash version, prefer a raw dictionary and a matching
generated registry if the server exposes fields newer than this package.

`studio_filter(stash_id=...)` is normalized to the Stash schema's
`stash_id_endpoint` field. Other builders preserve the keyword names supplied.

## Criteria operators

Use these helpers as values inside a filter field:

| Helper | Modifier or shape | Meaning |
| --- | --- | --- |
| `equals(value)` | `EQUALS` | Exact match |
| `not_equals(value)` | `NOT_EQUALS` | Excludes an exact match |
| `includes(value)` | `INCLUDES` | Contains a value in a list or hierarchy |
| `includes_all(value)` | `INCLUDES_ALL` | Contains every supplied value |
| `excludes(value)` | `EXCLUDES` | Does not contain a value |
| `between(start, end)` | `BETWEEN` | Inclusive range using `value` and `value2` |
| `greater_than(value)` | `GREATER_THAN` | Greater than a value |
| `less_than(value)` | `LESS_THAN` | Less than a value |
| `matches_regex(pattern)` | `MATCHES_REGEX` | Regular-expression match |
| `not_matches_regex(pattern)` | `NOT_MATCHES_REGEX` | Regular-expression non-match |
| `is_null()` | `IS_NULL` | Null value |
| `not_null()` | `IS_NULL: false` | Non-null value |
| `stash_id(endpoint, value)` | external ID shape | One external ID |
| `stash_ids(endpoint, values)` | external IDs shape | Any of several external IDs |

Examples:

```python
from stashapp_client import (
	between,
	equals,
	find_filter,
	includes,
	includes_all,
	not_null,
	scene_filter,
)

filters = scene_filter(
	title=includes("vacation"),
	rating100=between(80, 100),
	date=not_null(),
	tags=includes_all([182, 205]),
	AND=[scene_filter(organized=equals(True))],
)
scenes = client.findScenes(scene_filter=filters, filter=find_filter(per_page=50))
```

Hierarchical criteria accept optional `depth` and `excludes` values:

```python
includes("parent-tag", depth=2, excludes=["archived-tag"])
```

For an operation or field not covered by a convenience helper, pass a raw
schema-shaped dictionary. The runtime validates known generated input fields
before sending the request:

```python
scenes = client.findScenes(
	scene_filter={
		"organized": False,
		"duration": {"modifier": "GREATER_THAN", "value": 600},
		"performers": {"modifier": "INCLUDES", "value": 84},
	}
)
```

## Generated API

::: stashapp_client.filters

::: stashapp_client.criteria
