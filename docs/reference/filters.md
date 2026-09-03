# Filters and criteria

Filter helpers return ordinary dictionaries shaped for Stash GraphQL input
objects. Pass them to the matching `*_filter` operation argument.

## Filter builders

The available builders are:

| Builder | Typical operations | Common fields |
| --- | --- | --- |
| `find_filter` | all `find*` operations | `q`, `page`, `per_page`, `sort`, `direction` |
| `scene_filter` | `findScenes` | `id`, `title`, `date`, `details`, `organized`, `rating100`, `duration`, `tags`, `performers`, `studios` |
| `image_filter` | `findImages` | `id`, `path`, `rating100`, `organized`, `date`, `galleries`, `studios`, `tags`, `performers` |
| `gallery_filter` | `findGalleries` | `id`, `title`, `date`, `organized`, `rating100`, `has_chapters`, `performers`, `studios`, `tags` |
| `performer_filter` | `findPerformers` | `id`, `name`, `gender`, `country`, `rating100`, `image_count`, `stash_id` |
| `studio_filter` | `findStudios` | `id`, `name`, `url`, `favorite`, `scene_count`, `image_count`, `stash_id` |
| `tag_filter` | `findTags` | `id`, `name`, `favorite`, `scene_count`, `image_count`, `stash_id` |
| `group_filter` | `findGroups` | `id`, `name`, `rating100`, `scene_count`, `performers`, `studios`, `tags` |
| `marker_filter` | `findMarkers` | `id`, `title`, `seconds`, `duration`, `scene_id`, `tags` |

All builders accept `AND`, `OR`, and `NOT` for boolean composition. They reject
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
