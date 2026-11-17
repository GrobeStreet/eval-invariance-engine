import pytest
pytest.importorskip("inspect_ai")
from inspect_ai import Task, eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import get_model, ModelOutput
from eval_invariance_engine.inspect_adapter import cyclic_mcq_task, invariance_task


def samples():
    return [Sample(id="q1", input="2+2=?", choices=["4", "5", "6", "7"], target="A",
                   metadata={"source": "toy"}),
            Sample(id="q2", input="Capital of France?", choices=["Paris", "Rome", "Bonn", "Madrid"], target="A")]


def test_expansion_preserves_answers_identity_and_source_metadata():
    task = cyclic_mcq_task(samples())
    variants = list(task.dataset)
    assert len(variants) == 8
    assert len({sample.id for sample in variants}) == 8
    for sample in variants:
        line = next(line for line in sample.input.splitlines() if line.startswith(sample.target + "."))
        expected = "4" if sample.metadata["invariance_group"] == "q1" else "Paris"
        assert line.split(". ", 1)[1] == expected
        if expected == "4":
            assert sample.metadata["source"] == "toy"
        assert sample.metadata["invariance_expected_conditions"] == ["shift0", "shift1", "shift2", "shift3"]


def test_old_task_wrapper_requires_explicit_rebuild():
    original = Task(dataset=MemoryDataset(samples()), metadata={"keep": "original"})
    with pytest.raises(ValueError, match="does not preserve Task semantics"):
        invariance_task(original)
    rebuilt = invariance_task(original, rebuild=True)
    assert original.metadata == {"keep": "original"}
    assert len(list(original.dataset)) == 2
    assert rebuilt.metadata["invariance_task_mode"].startswith("new generate-only")


@pytest.mark.parametrize("data", [
    [],
    [Sample(input="free text", target="x")],
    [Sample(input="q", choices=["yes", "no"], target=["A", "B"])],
    [Sample(id="same", input="q", choices=["yes", "no"], target="A")] * 2,
    [Sample(input="q", choices=["yes", "no"], target="A"),
     Sample(input="r", choices=["yes", "no", "maybe"], target="A")],
    [Sample(input="q", choices=["yes", "no"], target="A", metadata={"invariance_group": "fake"})],
])
def test_unsupported_samples_fail_instead_of_silent_skips(data):
    with pytest.raises(ValueError):
        cyclic_mcq_task(data)


@pytest.mark.parametrize("completion,expected", [("A", 1), ("Answer is B", 0)])
def test_mock_inspect_eval_runs_without_provider_keys_or_network(tmp_path, completion, expected):
    # mockllm is Inspect's built-in local provider. Deterministic A responses.
    task = cyclic_mcq_task(samples())
    model = get_model("mockllm/model", custom_outputs=[ModelOutput.from_content("mock", completion) for _ in range(8)])
    logs = eval(task, model=model, display="none", log_dir=str(tmp_path),
                log_format="json", epochs=1)
    assert logs[0].status == "success", logs[0].error
    values = {key.split("/")[-1]: item.value for score in logs[0].results.scores
              for key, item in score.metrics.items()}
    assert values["invariance_drift"] == expected
    assert values["invariance_correctness_flip_rate"] == expected
    for sample in logs[0].samples:
        scored = next(iter(sample.scores.values()))
        assert scored.metadata["valid_answer"] is bool(expected)
