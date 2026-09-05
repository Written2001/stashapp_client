"""Stash client configuration and low-level GraphQL execution."""

from __future__ import annotations

import os
import ssl
import time
from pathlib import Path
from typing import Any

import requests
from requests import Session
from requests.adapters import HTTPAdapter

from .criteria import equals
from .errors import StashConnectionError, StashResponseError, TransportError
from .filters import performer_filter, studio_filter, tag_filter
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
        """Create a client and bind operations from a generated registry.

        Args:
            url: Stash GraphQL endpoint URL.
            api_key: API key sent in the ``ApiKey`` request header.
            verify: TLS verification setting or a CA bundle path.
            timeout: HTTP request timeout in seconds.
            session: Optional requests-compatible session, useful for testing.
            registry_path: Optional path to a generated operations registry.
        """
        if not url:
            raise ValueError("url is required")
        if not api_key:
            raise ValueError("api_key is required")
        self.url = url
        self.api_key = api_key
        self.verify = verify
        self.timeout = timeout
        self.session = session or requests.Session()
        if isinstance(verify, str) and session is None:
            self.session.mount("https://", _CustomCABundleAdapter(verify))
        selected_registry = (
            Path(registry_path)
            if registry_path
            else Path(__file__).parent / "generated" / "operations_registry.json"
        )
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
        """Create a client from URL and API-key lines in a credentials file."""
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
        """Create a client from ``STASH_URL`` and ``STASH_API_KEY``."""
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
        """Execute a GraphQL document and select the requested result shape.

        Args:
            query: GraphQL document to send to the endpoint.
            variables: Optional GraphQL variables mapping.
            response: ``data`` for extracted values, ``object`` for data plus
                metadata, or ``raw`` for the complete GraphQL envelope.
            field: Optional response path, as a dotted string component or list
                of components.

        Raises:
            TransportError: The HTTP request or TLS connection failed.
            StashResponseError: The server returned invalid JSON or structure.
            GraphQLError: The envelope contains GraphQL errors in data mode.
        """
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
        """Validate the endpoint with a minimal GraphQL request."""
        try:
            self.execute("query ConnectionCheck { __typename }")
        except Exception as exc:
            raise StashConnectionError(str(exc)) from exc
        return True

    def wait_for_job(
        self,
        job_id: str,
        check_interval: float = 60,
        timeout: float | None = None,
        verbose: bool = True,
    ) -> dict[str, Any]:
        """Poll a Stash job until it reaches a terminal state."""
        _validate_wait_for_job(job_id, check_interval, timeout, verbose)
        started_at = time.monotonic()
        while True:
            result = self.__dict__["findJob"](input={"id": job_id})
            job = result.get("findJob") if isinstance(result, dict) else None
            if not isinstance(job, dict):
                raise StashResponseError("findJob returned an invalid job response")
            status = str(job.get("status", "")).upper()
            if status in {"FINISHED", "COMPLETED"}:
                return job
            if status in {"FAILED", "CANCELLED", "CANCELED"}:
                raise StashResponseError(f"Stash job {job_id} ended with status {status}")
            if status not in {"WAITING", "PENDING", "RUNNING"}:
                raise StashResponseError(f"Stash job {job_id} returned unknown status: {status}")
            elapsed = time.monotonic() - started_at
            if timeout is not None and elapsed >= timeout:
                raise StashResponseError(f"Timed out waiting for Stash job {job_id}")
            if verbose:
                print(f"Stash job {job_id} is still {status}")
            delay = check_interval
            if timeout is not None:
                delay = min(delay, max(0, timeout - elapsed))
            time.sleep(delay)

    def find_studio_id(self, name: str, multiple: str = "error") -> str | list[str]:
        """Find a studio ID by exact name."""
        return self._find_named_id(
            name,
            multiple,
            self.__dict__["findStudios"],
            studio_filter(name=equals(name)),
            "studio_filter",
            "studios",
        )

    def find_tag_id(self, name: str, multiple: str = "error") -> str | list[str]:
        """Find a tag ID by exact name."""
        return self._find_named_id(
            name,
            multiple,
            self.__dict__["findTags"],
            tag_filter(name=equals(name)),
            "tag_filter",
            "tags",
        )

    def find_performer_id(self, name: str, multiple: str = "error") -> str | list[str]:
        """Find a performer ID by exact name."""
        return self._find_named_id(
            name,
            multiple,
            self.__dict__["findPerformers"],
            performer_filter(name=equals(name)),
            "performer_filter",
            "performers",
        )

    @staticmethod
    def _find_named_id(
        name: str,
        multiple: str,
        finder: Any,
        criterion: dict[str, Any],
        filter_argument: str,
        result_field: str,
    ) -> str | list[str]:
        _validate_named_lookup(name, multiple)
        ids = finder(**{filter_argument: criterion}, field=[result_field, "id"])
        if not isinstance(ids, list) or not ids:
            raise StashResponseError(f"No object found with exact name: {name}")
        if multiple == "error" and len(ids) > 1:
            raise StashResponseError(f"Multiple objects found with exact name: {name}")
        if multiple == "first":
            return str(ids[0])
        if multiple == "all":
            return [str(identifier) for identifier in ids]
        return str(ids[0])

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()

    def __enter__(self) -> "StashClient":  # noqa: PYI034, UP037
        """Return this client for use in a context manager."""
        return self

    def __exit__(self, *args: object) -> None:
        """Close the client when leaving a context manager."""
        self.close()


def _parse_verify(value: str) -> bool | str:
    lowered = value.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value


def _validate_wait_for_job(
    job_id: str, check_interval: float, timeout: float | None, verbose: bool
) -> None:
    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("job_id must be a single non-empty string")
    if isinstance(check_interval, bool) or not isinstance(check_interval, (int, float)):
        raise TypeError("check_interval must be a single non-negative number")
    if check_interval < 0:
        raise ValueError("check_interval must be a single non-negative number")
    if timeout is not None and (
        isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout < 0
    ):
        exception = TypeError if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) else ValueError
        raise exception("timeout must be a single non-negative number or None")
    if not isinstance(verbose, bool):
        raise TypeError("verbose must be a boolean")


def _validate_named_lookup(name: str, multiple: str) -> None:
    if not isinstance(name, str) or not name:
        raise ValueError("name must be a non-empty string")
    if multiple not in {"error", "first", "all"}:
        raise ValueError("multiple must be one of: error, first, all")


class _CustomCABundleAdapter(HTTPAdapter):
    """Use a custom CA bundle with compatibility for older self-signed CAs."""

    def __init__(self, cafile: str) -> None:
        self.cafile = cafile
        super().__init__()

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        context = ssl.create_default_context(cafile=self.cafile)
        strict_flag = getattr(ssl, "VERIFY_X509_STRICT", 0)
        context.verify_flags &= ~strict_flag
        kwargs["ssl_context"] = context
        super().init_poolmanager(*args, **kwargs)
