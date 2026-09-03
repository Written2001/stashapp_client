# stashapp-client

An SDL-first Python client for the [Stash](https://github.com/stashapp/stash) GraphQL API. The package generates an operation registry from the Stash schema and binds query and mutation methods to `StashClient` at runtime.

## Installation

Install the latest published release from PyPI:

```bash
python -m pip install stashapp-client
```

For development from a checkout of this repository:

```bash
python -m pip install -e .
```

For development tools:

```bash
python -m pip install -e '.[dev]'
```

Releases follow [Semantic Versioning](https://semver.org/). See
[`CHANGELOG.md`](CHANGELOG.md) for release history.

Read the full documentation at
<https://written2001.github.io/stashapp_client/>.

## Connect

Create a credentials file containing the GraphQL URL and API key on separate lines:

```text
https://stash.example/graphql
YOUR_API_KEY
```

Then create a client:

```python
from stashapp_client import StashClient

client = StashClient.from_credentials_file(".stash_credentials")
print(client.has_connection())
```

Credentials can also come directly from arguments or environment variables:

```python
client = StashClient(
    url="https://stash.example/graphql",
    api_key="YOUR_API_KEY",
)

# Reads STASH_URL and STASH_API_KEY.
client = StashClient.from_env()
```

Always close the client when finished, or use it as a context manager:

```python
with StashClient.from_credentials_file(".stash_credentials") as client:
    print(client.findTags())
```

## TLS

Pass `verify=False` only for a trusted internal endpoint. A CA bundle path is preferred for self-signed certificates:

```python
client = StashClient.from_credentials_file(
    ".stash_credentials",
    verify="/path/to/internal-ca.pem",
)
```

`STASHAPI_TLS_VERIFY=false` disables verification, while a path value selects a CA bundle.

## Use The API

Operation methods are created from the bundled registry, so queries and mutations use schema-defined names and keyword arguments:

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

tags = client.findTags(
    tag_filter={"favorite": True},
    filter=find_filter(per_page=50),
)
```

Filter arguments use the GraphQL operation names, such as `scene_filter`,
`gallery_filter`, and `tag_filter`. The `*_filter()` helpers cover common
criteria and reject unknown helper fields. You can also pass a raw dictionary
for any field in the generated schema:

```python
scenes = client.findScenes(
    scene_filter={
        "organized": False,
        "duration": {"modifier": "GREATER_THAN", "value": 600},
        "performers": {"modifier": "INCLUDES", "value": 84},
    }
)
```

Mutations use the same generated operation methods and schema-defined argument names:

```python
new_tag = client.tagCreate(input={"name": "Reviewed"})
client.tagDestroy(input={"id": "123"})
```

Set `per_page` to `-1` to fetch all pages of a list result:

```python
all_tags = client.findTags(filter={"per_page": -1})
```

List-of-object results are returned as `pandas.DataFrame`; scalar results are returned as ordinary Python values. Use `field` to extract a response path and `response` to control the response shape:

```python
titles = client.findScenes(field=["scenes", "title"])
count = client.findTags(field="count")
metadata = client.findTags(response="object")
envelope = client.findTags(response="raw")
```

Nested DataFrame columns remain as Python lists or dictionaries. Optional helpers are available for common transformations:

```python
from stashapp_client.response import explode_column, flatten_column

flat = flatten_column(scenes, "studio")
tags = explode_column(scenes, "tags")
```

## Generate Operations

The bundled registry is generated from the Stash schema. Build artifacts from a schema snapshot with:

```bash
stashapp-client build-ops --schema ./schema.json
```

This writes `schema.json`, `operations_registry.json`, `fragments.py`, and `inputs.py` to the current directory by default. Override any output with `--out-schema`, `--out-registry`, `--out-fragments`, or `--out-inputs`.

Regenerate from a live server:

```bash
stashapp-client sync-schema \
    --credentials-file .stash_credentials \
    --out-schema ./schema.json
```

Compare two schema snapshots before rebuilding:

```bash
stashapp-client diff-schema \
    --base ./schema.json \
    --current ./candidate-schema.json
```

`diff-schema` exits with status `1` when changes are found, which makes it suitable for CI.

## Custom Registry

Use a different generated registry when testing or targeting another schema version:

```python
client = StashClient(
    url="https://stash.example/graphql",
    api_key="YOUR_API_KEY",
    registry_path="./operations_registry.json",
)
```
