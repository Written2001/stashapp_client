from __future__ import annotations

from stashapp_client.mutation import prepare_mutations


def test_prepare_mutations_omits_missing_values_without_network() -> None:
    plan = prepare_mutations(
        [{"id": "101", "title": None, "ids": ["a", None]}],
        lambda row, index: {"id": row["id"], "title": row["title"], "ids": row["ids"]},
        operation="galleryUpdate",
    )

    assert plan.entries[0].input == {"id": "101", "ids": ["a"]}
    assert plan.entries[0].omitted == ("title",)
    assert plan.execute(lambda **kwargs: (_ for _ in ()).throw(AssertionError()))["results"][0]["status"] == "planned"


def test_execute_mutations_supports_continue_and_preserves_indexes() -> None:
    plan = prepare_mutations(
        [{"id": "101"}, {"id": "102"}, {"id": "103"}],
        lambda row, index: row,
    )

    def mutate(*, input: dict[str, str]) -> dict[str, str]:
        if input["id"] == "102":
            raise RuntimeError("bad input")
        return {"id": input["id"]}

    result = plan.execute(mutate, dry_run=False, on_error="continue")

    assert [entry["index"] for entry in result["results"]] == [1, 2, 3]
    assert [entry["status"] for entry in result["results"]] == ["succeeded", "failed", "succeeded"]


def test_execute_mutations_supports_non_input_argument() -> None:
    plan = prepare_mutations(
        [["101", "102"]],
        lambda row, index: {"ids": row},
    )
    calls: list[dict[str, object]] = []

    result = plan.execute(
        lambda **kwargs: calls.append(kwargs) or True,
        dry_run=False,
        argument="ids",
    )

    assert result["results"][0]["status"] == "succeeded"
    assert calls == [{"ids": ["101", "102"]}]
