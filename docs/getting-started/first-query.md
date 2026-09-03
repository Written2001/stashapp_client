# First query

Operation methods are loaded from the bundled registry. A list operation returns a pandas DataFrame by default:

```python
from stashapp_client import StashClient, find_filter, scene_filter

with StashClient.from_env() as client:
    scenes = client.findScenes(
        scene_filter=scene_filter(title={"modifier": "INCLUDES", "value": "demo"}),
        filter=find_filter(per_page=25),
    )

print(scenes[["id", "title"]])
```

The generated operation name and argument names are schema-defined. Use the [queries and filters guide](../guide/queries-and-filters.md) for richer criteria and the [responses guide](../guide/responses-and-dataframes.md) for extracting nested values.
