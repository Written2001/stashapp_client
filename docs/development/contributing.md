# Contributing

Development setup, testing, generated artifacts, and pull request expectations are documented in the repository's [CONTRIBUTING.md](https://github.com/Written2001/stashapp_client/blob/main/CONTRIBUTING.md).

The short version:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check src tools tests
```

Keep generated schema artifacts together and do not commit credentials, certificates, notebooks, caches, or build output.
