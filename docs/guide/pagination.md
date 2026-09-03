# Pagination

Pass the GraphQL `filter` argument to control page size and ordering:

```python
first_page = client.findTags(filter={"per_page": 50, "page": 1})
```

Set `per_page` to `-1` to request all pages. The client automatically follows pages for list operations and merges the results:

```python
all_tags = client.findTags(filter={"per_page": -1})
```

Use a bounded page size when working with large libraries or when you need predictable request and memory limits.
