# Contributing

Thanks for contributing to `stashapp-client`. This project is an SDL-first client for the Stash GraphQL API. Keep runtime behavior schema-driven and avoid hand-editing generated artifacts.

## Development Setup

The project requires Python 3.10 or newer.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Run the checks before opening a pull request:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check src tools tests
```

Build the documentation locally when changing `docs/` or `mkdocs.yml`:

```bash
python -m pip install -e '.[docs]'
mkdocs serve
mkdocs build --strict
```

The GitHub Actions workflow also builds a wheel, validates its metadata, and installs it into a clean virtual environment.

Do not commit credentials, certificates, virtual environments, notebooks, caches, build output, or `*.egg-info` directories. The repository ignores these files by default.

## Generated Artifacts

The checked-in files under `src/stashapp_client/generated/` are runtime package data:

- `schema.json`: normalized schema snapshot
- `operations_registry.json`: operation metadata and GraphQL documents
- `fragments.py`: generated fragment definitions
- `inputs.py`: generated input metadata and validation support

Regenerate all four together. Do not edit them by hand.

## Generate From Pinned Stash SDL

The canonical generation source is a pinned Stash checkout, not live introspection. For example, the current package schema was generated from Stash `v0.31.1` at commit `4de2351e7cc990d7ccd7cb6c84c275cd53bf6e55`:

```bash
python tools/generate_registry.py \
    --source-root /tmp/stashapp-stash-v0.31.1 \
    --ref v0.31.1 \
    --commit 4de2351e7cc990d7ccd7cb6c84c275cd53bf6e55 \
    --package-version v0.31.1 \
    --schema-output src/stashapp_client/generated/schema.json \
    --registry-output src/stashapp_client/generated/operations_registry.json \
    --fragments-output src/stashapp_client/generated/fragments.py \
    --inputs-output src/stashapp_client/generated/inputs.py
```

The checkout must contain Stash GraphQL SDL under `graphql/schema/types/` or `graphql/schema/`. The generator records the source ref, commit, SDL file list, and file fingerprints in the generated registry provenance.

To build artifacts from an existing schema snapshot instead:

```bash
python tools/generate_registry.py \
    --schema ./schema.json \
    --registry-output src/stashapp_client/generated/operations_registry.json \
    --fragments-output src/stashapp_client/generated/fragments.py \
    --inputs-output src/stashapp_client/generated/inputs.py
```

## When Stash Releases A New Version

Treat a Stash schema upgrade as a deliberate client release:

1. Check out the exact Stash tag or commit and record both the human-readable ref and immutable commit SHA.
2. Compare the old and new schema snapshots:

   ```bash
   stashapp-client diff-schema \
       --base src/stashapp_client/generated/schema.json \
       --current /path/to/new-schema.json
   ```

   A difference report exits with status `1`; that is expected when changes are found. Review removed fields, changed types, new required arguments, deprecations, and input changes.
3. Regenerate `schema.json`, `operations_registry.json`, `fragments.py`, and `inputs.py` from the new pinned checkout using the command above.
4. Validate every generated document against the new schema and run the complete test and lint checks.
5. Add or update tests for changed operations, filters, inputs, response paths, and recursive or abstract types.
6. Update `CHANGELOG.md` and bump the client version according to SemVer:
   - Patch: bug fixes and compatible generated changes
   - Minor: new compatible API capabilities
   - Major: breaking Python or GraphQL API behavior
7. Review the generated diff. Confirm the registry provenance names the new Stash ref and commit, and confirm no credentials or local files entered the change.
8. Commit the source and generated artifacts together, then publish a matching Git tag such as `v0.2.0` through a GitHub Release.

Live introspection is available for diagnostics or when a Stash checkout is not available:

```bash
stashapp-client sync-schema \
    --credentials-file .stash_credentials \
    --out-schema ./schema.json \
    --out-registry ./operations_registry.json
```

Do not use an unrecorded live schema as the basis for a release. Copy it into the generated package only after its Stash version and provenance have been identified.

## Local Distribution Checks

Install build tooling and validate a release locally:

```bash
.venv/bin/python -m pip install build twine
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

For a clean wheel smoke test:

```bash
python -m venv /tmp/stashapp-client-wheel
/tmp/stashapp-client-wheel/bin/python -m pip install dist/*.whl
/tmp/stashapp-client-wheel/bin/python -c "import stashapp_client; print(stashapp_client.StashClient)"
```

The publish workflow performs these checks automatically when a GitHub Release is published. PyPI publishing uses trusted publishing; do not add PyPI tokens to the repository or workflow files.

## Pull Requests

Keep pull requests focused. Include tests for behavior changes, update generated artifacts when the schema or generator changes, and describe any Stash-version dependency in the changelog or pull request description.
