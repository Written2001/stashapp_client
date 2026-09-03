# Mutations

Mutations use generated operation methods and schema-defined arguments:

```python
new_tag = client.tagCreate(input={"name": "Reviewed"})
client.tagDestroy(input={"id": "123"})
```

For batch work, `prepare_mutations` normalizes rows without making network requests. Plans default to dry-run execution:

```python
from stashapp_client import prepare_mutations

plan = prepare_mutations(
    [{"name": "One"}, {"name": "Two"}],
    lambda row, index: {"input": row},
    operation="tagCreate",
)

preview = plan.execute(client.tagCreate)
result = plan.execute(client.tagCreate, dry_run=False, on_error="continue")
```

Use `na="error"` or `null="error"` when omitted values should stop plan creation rather than be removed.
