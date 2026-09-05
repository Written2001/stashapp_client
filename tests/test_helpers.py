from __future__ import annotations

from typing import Any

import pytest

from stashapp_client import StashClient
from stashapp_client.errors import StashResponseError


class FakeSession:
    def close(self) -> None:
        return None


def make_client() -> StashClient:
    return StashClient("https://stash/graphql", "secret", session=FakeSession())  # type: ignore[arg-type]


def test_wait_for_job_polls_until_finished(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    jobs = [
        {"findJob": {"id": "job-1", "status": "RUNNING"}},
        {"findJob": {"id": "job-1", "status": "FINISHED", "progress": 1}},
    ]
    inputs: list[dict[str, Any]] = []
    delays: list[float] = []

    def find_job(**kwargs: Any) -> dict[str, Any]:
        inputs.append(kwargs)
        return jobs.pop(0)

    monkeypatch.setattr(client, "findJob", find_job)
    monkeypatch.setattr("stashapp_client.client.time.sleep", delays.append)

    result = client.wait_for_job("job-1", check_interval=5, verbose=False)

    assert result["status"] == "FINISHED"
    assert inputs == [{"input": {"id": "job-1"}}, {"input": {"id": "job-1"}}]
    assert delays == [5]


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED", "CANCELED"])
def test_wait_for_job_raises_for_failed_jobs(status: str) -> None:
    client = make_client()
    client.findJob = lambda **kwargs: {  # type: ignore[method-assign]
        "findJob": {"id": "job-1", "status": status}
    }

    with pytest.raises(StashResponseError, match=f"status {status}"):
        client.wait_for_job("job-1", verbose=False)


def test_wait_for_job_raises_for_unknown_status() -> None:
    client = make_client()
    client.findJob = lambda **kwargs: {  # type: ignore[method-assign]
        "findJob": {"id": "job-1", "status": "PAUSED"}
    }

    with pytest.raises(StashResponseError, match="unknown status: PAUSED"):
        client.wait_for_job("job-1", verbose=False)


def test_wait_for_job_raises_when_timeout_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    client.findJob = lambda **kwargs: {  # type: ignore[method-assign]
        "findJob": {"id": "job-1", "status": "RUNNING"}
    }
    times = iter([0.0, 2.0])
    monkeypatch.setattr("stashapp_client.client.time.monotonic", lambda: next(times))

    with pytest.raises(StashResponseError, match="Timed out waiting"):
        client.wait_for_job("job-1", timeout=1, verbose=False)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"job_id": "", "verbose": False}, "job_id"),
        ({"job_id": "job-1", "check_interval": -1}, "check_interval"),
        ({"job_id": "job-1", "timeout": -1}, "timeout"),
        ({"job_id": "job-1", "verbose": 1}, "verbose"),
    ],
)
def test_wait_for_job_validates_arguments(kwargs: dict[str, Any], message: str) -> None:
    exception = TypeError if message == "verbose" else ValueError
    with pytest.raises(exception, match=message):
        make_client().wait_for_job(**kwargs)


def test_find_tag_id_uses_exact_name_and_multiple_policies() -> None:
    client = make_client()
    calls: list[dict[str, Any]] = []

    def find_tags(**kwargs: Any) -> list[str]:
        calls.append(kwargs)
        return ["12", "13"]

    client.findTags = find_tags  # type: ignore[method-assign]

    with pytest.raises(StashResponseError, match="Multiple objects"):
        client.find_tag_id("Example Tag")
    assert client.find_tag_id("Example Tag", multiple="first") == "12"
    assert client.find_tag_id("Example Tag", multiple="all") == ["12", "13"]
    assert calls[0] == {
        "tag_filter": {"name": {"modifier": "EQUALS", "value": "Example Tag"}},
        "field": ["tags", "id"],
    }


def test_find_named_id_helpers_support_studio_and_performer() -> None:
    client = make_client()
    studio_calls: list[dict[str, Any]] = []
    performer_calls: list[dict[str, Any]] = []

    def find_studios(**kwargs: Any) -> list[str]:
        studio_calls.append(kwargs)
        return ["studio-1"]

    def find_performers(**kwargs: Any) -> list[str]:
        performer_calls.append(kwargs)
        return ["performer-1"]

    client.findStudios = find_studios  # type: ignore[method-assign]
    client.findPerformers = find_performers  # type: ignore[method-assign]

    assert client.find_studio_id("Example Studio") == "studio-1"
    assert client.find_performer_id("Example Performer") == "performer-1"
    assert studio_calls[0]["field"] == ["studios", "id"]
    assert performer_calls[0]["field"] == ["performers", "id"]


def test_find_named_id_raises_for_missing_or_invalid_matches() -> None:
    client = make_client()
    client.findTags = lambda **kwargs: []  # type: ignore[method-assign]

    with pytest.raises(StashResponseError, match="No object"):
        client.find_tag_id("Missing")
    with pytest.raises(ValueError, match="multiple must be"):
        client.find_tag_id("Example", multiple="many")
    with pytest.raises(ValueError, match="name"):
        client.find_tag_id("")
