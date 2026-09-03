# stashapp-client

`stashapp-client` is an SDL-first Python client for the [Stash](https://github.com/stashapp/stash) GraphQL API.

It bundles schema-derived operation documents and binds them to `StashClient` at runtime. Query and mutation methods follow the names and argument shapes defined by the bundled Stash schema.

## Start here

- [Install the package](getting-started/installation.md)
- [Connect to a Stash server](getting-started/connection.md)
- [Run your first query](getting-started/first-query.md)
- [Browse the API reference](reference/client.md)

## Design principles

- **Schema-first:** generated operations and input validation follow a pinned Stash schema.
- **Python-friendly:** list results become pandas DataFrames, while scalar results remain ordinary Python values.
- **Inspectable:** response modes, field extraction, dry-run mutation plans, and custom registries make behavior visible and testable.

The source repository, issue tracker, and release history are available through the links in the site header.
