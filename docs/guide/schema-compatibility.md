# Schema compatibility

The package ships generated operations for a pinned Stash schema. The registry contains the operation documents, input metadata, field metadata, and provenance for that schema.

A client can use another generated registry when targeting a different compatible schema:

```python
client = StashClient(
    url="https://stash.example/graphql",
    api_key="YOUR_API_KEY",
    registry_path="./operations_registry.json",
)
```

For schema upgrades, compare snapshots before regenerating the package artifacts. Review removed fields, changed types, new required arguments, deprecations, and input changes. See [schema generation](../development/schema-generation.md) for the maintainer workflow.
