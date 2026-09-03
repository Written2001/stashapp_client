# Changelog

All notable changes to this project are documented here.

This project follows [Semantic Versioning](https://semver.org/).

## [0.1.5] - 2026-09-03

- Fixed nested response field selection when the requested path crosses a
	GraphQL fragment spread.
- Expanded filter helpers to accept all fields from the generated GraphQL
	filter input types, including performer fields such as `hair_color`.
- Documented the complete allowed field set for every filter helper.
- Automated GitHub Releases and PyPI publication for merges into `main`.

## [0.1.4] - 2026-09-03

- Added a complete MkDocs documentation site and GitHub Pages deployment workflow.
- Expanded filters and criteria documentation with operators, composition, strict mode, and raw input examples.
- Improved public API docstrings for client lifecycle, responses, pagination, mutations, schema tooling, validation, and runtime binding.
- Added documentation dependencies and local documentation development commands.

## [0.1.3] - 2026-09-02

- Fixed manual release recovery to run the current top-level workflow against a selected tag.

## [0.1.2] - 2026-09-02

- Added a top-level release workflow that creates GitHub Releases and publishes distributions to PyPI.
- Made automated release creation safe to rerun for an existing tag.

## [0.1.1] - 2026-09-02

- Added automated GitHub Release creation for SemVer tags.
- Added manual PyPI publishing through GitHub Actions.
- Added release-tag validation before publishing.

## [0.1.0] - 2026-09-02

- First public release.
- Added dynamic GraphQL operation binding from generated schema metadata.
- Added response extraction, pagination, filters, mutation helpers, and schema tooling.
- Added generated Stash schema, operation registry, fragments, and input metadata.
- Added Python package distribution, CLI tooling, CI, and PyPI publishing configuration.
