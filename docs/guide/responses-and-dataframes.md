# Responses and DataFrames

The default `response="data"` mode returns the GraphQL data payload. List-of-object results are converted to pandas DataFrames; scalar results remain ordinary Python values.

Use `field` to extract a path from the result:

```python
titles = client.findScenes(field=["scenes", "title"])
count = client.findTags(field="count")
```

Use `response="object"` to preserve data and response metadata, or `response="raw"` to receive the complete GraphQL envelope:

```python
metadata = client.findTags(response="object")
envelope = client.findTags(response="raw")
```

Raw responses cannot be combined with field extraction. GraphQL errors raise `GraphQLError` in data mode; object mode preserves partial data and error metadata.

For nested DataFrame values, use the optional helpers:

```python
from stashapp_client.response import explode_column, flatten_column

flat = flatten_column(scenes, "studio")
expanded = explode_column(scenes, "tags")
```
