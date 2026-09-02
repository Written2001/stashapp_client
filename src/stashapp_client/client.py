"""Stash client configuration and low-level GraphQL execution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from requests import Session

from .errors import StashConnectionError, StashResponseError, TransportError
from .response import extract_response
from .runtime_bind import load_and_bind


class StashClient:
    """A configured client for one Stash GraphQL endpoint."""

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        verify: bool | str = True,
        timeout: float = 30,
        session: Session | None = None,
        registry_path: str | os.PathLike[str] | None = None,
    ) -> None:
        if not url:
            raise ValueError("url is required")
        if not api_key:
            raise ValueError("api_key is required")
        self.url = url
        self.api_key = api_key
        self.verify = verify
        self.timeout = timeout
        self.session = session or requests.Session()
        selected_registry = registry_path or Path(__file__).parent / "generated" / "operations_registry.json"
        if selected_registry.exists():
            load_and_bind(self, str(selected_registry))

    @classmethod
    def from_credentials_file(
        cls,
        path: str | os.PathLike[str],
        *,
        verify: bool | str = True,
        timeout: float = 30,
        **kwargs: Any,
    ) -> "StashClient":  # noqa: UP037
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        values = [line.strip() for line in lines if line.strip()]
        if len(values) < 2:
            raise ValueError("credentials file must contain URL and API key")
        if isinstance(verify, str) and not os.path.isabs(verify):
            verify = str(Path(path).parent / verify)
        return cls(values[0], values[1], verify=verify, timeout=timeout, **kwargs)

    @classmethod
    def from_env(
        cls, *, verify: bool | str = True, timeout: float = 30, **kwargs: Any
    ) -> "StashClient":  # noqa: UP037
        configured_verify = os.environ.get("STASHAPI_TLS_VERIFY")
        if configured_verify is not None:
            verify = _parse_verify(configured_verify)
        return cls(
            os.environ.get("STASH_URL", ""),
            os.environ.get("STASH_API_KEY", ""),
            verify=verify,
            timeout=timeout,
            **kwargs,
        )

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        response: str = "data",
        field: str | list[str] | None = None,
    ) -> Any:
        """Execute a GraphQL document and extract its result."""
        try:
            result = self.session.post(
                self.url,
                json={"query": query, "variables": variables or {}},
                headers={"ApiKey": self.api_key, "Content-Type": "application/json"},
                verify=self.verify,
                timeout=self.timeout,
            )
            result.raise_for_status()
            envelope = result.json()
        except requests.RequestException as exc:
            raise TransportError(str(exc)) from exc
        except ValueError as exc:
            raise StashResponseError("server returned invalid JSON") from exc
        if not isinstance(envelope, dict):
            raise StashResponseError("GraphQL response must be a JSON object")
        return extract_response(envelope, response=response, field=field)

    def has_connection(self) -> bool:
        """Return whether the endpoint accepts a minimal GraphQL request."""
        try:
            self.execute("query ConnectionCheck { __typename }")
        except Exception as exc:
            raise StashConnectionError(str(exc)) from exc
        return True

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "StashClient":  # noqa: PYI034, UP037
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def _parse_verify(value: str) -> bool | str:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value
