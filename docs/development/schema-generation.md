# Schema generation

The canonical package artifacts are generated from a pinned Stash checkout. The generator records the source ref, immutable commit, SDL file list, and fingerprints in registry provenance.

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

Compare snapshots before rebuilding:

```bash
stashapp-client diff-schema \
    --base src/stashapp_client/generated/schema.json \
    --current /path/to/new-schema.json
```

Review the generated diff and run the complete test and lint suite before releasing.
