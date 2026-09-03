# Troubleshooting

## Connection errors

Check that the URL includes the GraphQL endpoint, the API key is valid, and the server is reachable from the machine running Python. `has_connection()` performs a minimal GraphQL request and raises `StashConnectionError` when transport or response handling fails.

## TLS errors

Keep verification enabled whenever possible. For an internal CA, pass the CA bundle path through `verify` or `STASHAPI_TLS_VERIFY`. Avoid disabling verification unless the endpoint is trusted and isolated.

## GraphQL errors

In the default data response mode, GraphQL errors raise `GraphQLError`. Use `response="object"` when inspecting partial data and error metadata, or `response="raw"` when debugging the complete server envelope.

## Unexpected fields or arguments

Generated operations follow the bundled schema. If your Stash server is newer or older than that schema, generate a registry from the matching schema and pass its path with `registry_path`.
