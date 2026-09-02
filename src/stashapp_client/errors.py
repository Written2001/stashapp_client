"""Exceptions raised by the Stash client."""

from typing import Any


class StashError(Exception):
    """Base class for client errors."""


class TransportError(StashError):
    """A network, TLS, or timeout error occurred."""


class StashConnectionError(TransportError):
    """The endpoint could not be validated as a Stash GraphQL server."""


class StashResponseError(StashError):
    """The server response was not a valid GraphQL response."""


class GraphQLError(StashError):
    """The server returned one or more GraphQL errors."""

    def __init__(self, errors: list[dict[str, Any]], data: Any = None) -> None:
        self.errors = errors
        self.data = data
        message = "; ".join(str(error.get("message", error)) for error in errors)
        super().__init__(message or "GraphQL request failed")
