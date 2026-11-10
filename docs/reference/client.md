# Client API

::: stashapp_client.StashClient

## Helper methods

Use `wait_for_job` after a long-running mutation returns a job ID:

```python
job = client.wait_for_job(job_id, check_interval=30, timeout=3600)
```

The helper returns completed jobs and raises for failed, cancelled, unknown, or
timed-out jobs. Set `verbose=False` when the calling application provides its
own progress display.

For exact-name lookups, use the explicit ID helpers:

```python
studio_id = client.find_studio_id("Example Studio")
tag_ids = client.find_tag_id("Example Tag", multiple="all")
performer_id = client.find_performer_id("Example Performer")
```

Named lookups raise when there are no matches or multiple matches. Use
`multiple="first"` or `multiple="all"` to choose a different duplicate policy.

Generated operations use these default data-shape rules:

- List-of-object query results and bulk mutation results are pandas DataFrames.
- Single create and update mutation results are one-row pandas DataFrames.
- Supplying `field=` returns the selected scalar or list value instead.
- Nested dictionaries and lists inside DataFrame columns remain unflattened;
	use `flatten_column()` or `explode_column()` when needed.
