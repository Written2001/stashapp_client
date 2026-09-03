# Releases

Releases use Semantic Versioning and a matching Git tag. Update the version in `pyproject.toml`, add a dated entry to `CHANGELOG.md`, run the local distribution checks, and push the branch and tag.

```bash
python -m pytest -q
ruff check src tools tests
python -m build
python -m twine check dist/*

git push origin main
git push origin vX.Y.Z
```

The release workflow validates the tag against the package version, creates the GitHub Release, builds distributions, and publishes them to PyPI through Trusted Publishing. The PyPI publisher must authorize `release.yml` and the `pypi` GitHub environment.
