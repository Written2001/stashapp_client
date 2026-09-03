# Connect to Stash

`StashClient` requires the GraphQL endpoint URL and API key. A credentials file contains those values on separate non-empty lines:

```text
https://stash.example/graphql
YOUR_API_KEY
```

Load it with:

```python
from stashapp_client import StashClient

with StashClient.from_credentials_file(".stash_credentials") as client:
    print(client.has_connection())
```

You can also pass values directly:

```python
client = StashClient(
    url="https://stash.example/graphql",
    api_key="YOUR_API_KEY",
)
```

Or use environment variables:

```bash
export STASH_URL="https://stash.example/graphql"
export STASH_API_KEY="YOUR_API_KEY"
```

```python
client = StashClient.from_env()
```

## TLS verification

Verification is enabled by default. For a private certificate authority, pass its CA bundle path:

```python
client = StashClient.from_env(verify="/path/to/internal-ca.pem")
```

Use `verify=False` only for a trusted internal endpoint. The `STASHAPI_TLS_VERIFY` environment variable accepts `true`, `false`, or a CA bundle path.
