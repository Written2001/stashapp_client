from __future__ import annotations

import json
import ssl
from typing import Any

import pandas as pd
import pytest
from requests.adapters import HTTPAdapter

from stashapp_client import StashClient
from stashapp_client.errors import GraphQLError
from stashapp_client.response import explode_column, flatten_column


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(self.payload)

    def close(self) -> None:
        return None


def test_execute_sends_graphql_payload_and_extracts_data() -> None:
    session = FakeSession({"data": {"version": "0.31.1"}})
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    result = client.execute("query Version { version }")

    assert result == {"version": "0.31.1"}
    assert session.calls[0]["headers"]["ApiKey"] == "secret"
    assert session.calls[0]["json"] == {"query": "query Version { version }", "variables": {}}


def test_client_binds_operations_from_custom_registry(tmp_path: Any) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "operations": [
                    {"name": "version", "kind": "query", "arguments": [], "selection": "version"}
                ]
            }
        ),
        encoding="utf-8",
    )
    session = FakeSession({"data": {"version": "custom"}})

    client = StashClient(
        "https://stash/graphql",
        "secret",
        session=session,
        registry_path=registry_path,
    )

    assert client.version() == {"version": "custom"}


def test_object_response_preserves_metadata() -> None:
    session = FakeSession({"data": {"version": "0.31.1"}, "extensions": {"trace": True}})
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    assert client.execute("query Version { version }", response="object") == {
        "data": {"version": "0.31.1"},
        "meta": {"errors": None, "extensions": {"trace": True}},
    }


def test_object_response_preserves_extensions() -> None:
    session = FakeSession({"data": {"version": "0.31.1"}, "extensions": {"trace": True}})
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    assert client.execute("query Version { version }", response="object")["meta"] == {
        "errors": None,
        "extensions": {"trace": True},
    }


def test_partial_graphql_response_is_available_in_object_mode() -> None:
    session = FakeSession(
        {
            "data": {"version": "partial"},
            "errors": [{"message": "secondary field failed"}],
            "extensions": {"trace": True},
        }
    )
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    assert client.execute("query Version { version }", response="object") == {
        "data": {"version": "partial"},
        "meta": {
            "errors": [{"message": "secondary field failed"}],
            "extensions": {"trace": True},
        },
    }


def test_partial_graphql_response_raises_in_data_mode_with_partial_data() -> None:
    session = FakeSession(
        {"data": {"version": "partial"}, "errors": [{"message": "failed"}]}
    )
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(GraphQLError) as error:
        client.execute("query Version { version }")

    assert error.value.data == {"version": "partial"}


def test_raw_response_returns_complete_graphql_envelope() -> None:
    envelope = {
        "data": {"version": "partial"},
        "errors": [{"message": "secondary field failed"}],
        "extensions": {"trace": True},
    }
    session = FakeSession(envelope)
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    assert client.execute("query Version { version }", response="raw") == envelope


def test_raw_response_rejects_field_extraction() -> None:
    session = FakeSession({"data": {"version": "0.31.1"}})
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="field cannot be used"):
        client.execute("query Version { version }", response="raw", field="version")


def test_field_extraction_preserves_nullable_list_elements() -> None:
    session = FakeSession(
        {"data": {"performers": [{"eye_color": "blue"}, None]}}
    )
    client = StashClient("https://stash/graphql", "secret", session=session)  # type: ignore[arg-type]

    assert client.execute(
        "query Performers { performers { eye_color } }",
        field=["performers", "eye_color"],
    ) == ["blue", None]


def test_from_env_parses_tls_verify_setting(monkeypatch: Any) -> None:
    monkeypatch.setenv("STASH_URL", "https://stash/graphql")
    monkeypatch.setenv("STASH_API_KEY", "secret")
    monkeypatch.setenv("STASHAPI_TLS_VERIFY", "false")

    client = StashClient.from_env()

    assert client.verify is False
    client.close()


def test_custom_ca_bundle_supports_legacy_self_signed_certificates() -> None:
    ca_bundle = ssl.get_default_verify_paths().cafile
    assert ca_bundle is not None

    client = StashClient("https://stash/graphql", "secret", verify=ca_bundle)
    adapter = client.session.get_adapter("https://")
    assert isinstance(adapter, HTTPAdapter)
    context = adapter.poolmanager.connection_pool_kw["ssl_context"]

    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode is ssl.CERT_REQUIRED
    if hasattr(ssl, "VERIFY_X509_STRICT"):
        assert not context.verify_flags & ssl.VERIFY_X509_STRICT
    client.close()


def test_response_dataframe_helpers() -> None:
    frame = pd.DataFrame(
        [{"id": 1, "studio": {"name": "One"}, "tags": [{"name": "a"}, {"name": "b"}]}]
    )

    flattened = flatten_column(frame, "studio")
    assert flattened.to_dict("records") == [
        {"id": 1, "tags": [{"name": "a"}, {"name": "b"}], "studio.name": "One"}
    ]

    exploded = explode_column(frame, "tags")
    assert exploded["tags"].tolist() == [{"name": "a"}, {"name": "b"}]
