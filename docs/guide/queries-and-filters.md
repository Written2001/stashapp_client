# Queries and filters

The client binds generated query and mutation operations as methods on `StashClient`. Keyword arguments use the GraphQL argument names.

```python
from stashapp_client import between, find_filter, includes, scene_filter

scenes = client.findScenes(
    scene_filter=scene_filter(
        title=includes("vacation"),
        rating100=between(80, 100),
        tags=includes(182),
    ),
    filter=find_filter(per_page=50),
)
```

Convenience helpers cover common filter types and criteria. Raw dictionaries are useful when a generated schema exposes a field not covered by a convenience helper:

```python
scenes = client.findScenes(
    scene_filter={
        "organized": False,
        "duration": {"modifier": "GREATER_THAN", "value": 600},
        "performers": {"modifier": "INCLUDES", "value": 84},
    }
)
```

Input values are checked against generated input metadata before the request is sent. Unknown fields and invalid nested values fail early with a validation error.
