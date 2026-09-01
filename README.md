# eval-invariance-engine

**A benchmark score that moves when you cyclically reorder the answer options, jitter the whitespace, or change the seed is not measuring reasoning — it is measuring formatting-sensitivity and memorization.** This library quantifies that drift and ships a drop-in adapter, native metrics, and a CLI for [Inspect AI](https://inspect.aisi.org.uk), the evaluation harness standardizing across AI-safety work.

It generalizes the option-order robustness method from [`mmlu-robustness-audit`](https://github.com/GrobeStreet/mmlu-robustness-audit) into a reusable, framework-agnostic tool.

## Why

Leaderboards treat a headline score as ground truth. But the same model, on the same questions, can score several points differently when you change things that carry no meaning. If a score is not *invariant* to non-semantic perturbation, the ranking it produces is partly an artifact. This engine makes that fragility measurable — and re-runnable.

## Install

```bash
pip install eval-invariance-engine          # core, zero dependencies
pip install "eval-invariance-engine[inspect]"  # + Inspect AI integration
```

## CLI

```bash
invariance-check demo                          # built-in fragility demo
invariance-check report results.json           # score a results file, print the report
invariance-check report results.json --fail-on-fragile   # exit 1 if fragile — use it as a CI gate
```

`results.json` is either a mapping `{"shift0": [true, false, ...], ...}` or a list of
`{"condition": "shift0", "correct": true}` rows. `--fail-on-fragile` turns the check into a
regression gate: wire it into CI and a benchmark that starts drifting fails the build.

## Quickstart (framework-agnostic)

```python
from eval_invariance_engine import MCQItem, all_cyclic_variants, build_report

item = MCQItem("Capital of France?", ["Paris", "Rome", "Bonn", "Madrid"], answer_index=0)
results = {"shift0": [...], "shift1": [...], "shift2": [...], "shift3": [...]}  # bool per item
print(build_report(results).summary())
# [FRAGILE] n=... | drift=0.180 (95% CI 0.090-0.270) | flip_rate=0.31 | shift0=..., ...
```

## One line: audit any Inspect multiple-choice task

```python
from inspect_ai import eval
from eval_invariance_engine.inspect_adapter import invariance_task

# my_task is any Inspect Task whose samples have `choices` + `target`
eval(invariance_task(my_task), model="openai/gpt-4o-mini")
```

`invariance_task()` expands every item into all cyclic option orderings, scores them with the
invariance scorer, and attaches the drift + flip-rate metrics — so a single call turns an
existing benchmark into a fragility audit. Non-MCQ samples pass through untouched (skipped).

## Inspect AI integration — native metrics

`invariance_scorer()` attaches two custom `@metric`s — **`invariance_drift`** (max accuracy
spread across conditions) and **`invariance_flip_rate`** (fraction of items whose correctness
flips) — so the fragility numbers appear *inside the eval log* alongside accuracy, not just in
a post-hoc script.

```python
from inspect_ai import Task, eval
from inspect_ai.solver import generate
from inspect_ai.dataset import MemoryDataset
from eval_invariance_engine import MCQItem
from eval_invariance_engine.inspect_adapter import cyclic_variant_samples, invariance_scorer

items = [MCQItem("2+2=?", ["4", "5", "6", "7"], 0)]
samples = [s for i, it in enumerate(items) for s in cyclic_variant_samples(it, group_id=str(i))]

task = Task(dataset=MemoryDataset(samples), solver=generate(), scorer=invariance_scorer())
logs = eval(task, model="openai/gpt-4o-mini")
# logs[0] now carries `invariance_drift` and `invariance_flip_rate` in its metrics.
```

## Method

- **Perturbations** are deterministic and semantics-preserving: cyclic option reordering (the answer set is identical, only labels rotate) and whitespace restyling. The correct real-world answer never changes.
- **Report**: per-condition accuracy, `max_drift` (best - worst condition), `flip_rate` (fraction of items whose correctness flipped across conditions — the sharpest non-semantic-sensitivity signal), a bootstrap 95% CI on the drift, and a `fragile` / `invariant` verdict.
- **Deterministic** given a seed; the core is pure standard library.

## Status

`v0.3.0` — core, Inspect adapter, native `@metric`s, the `invariance-check` CLI, and the `invariance_task()` one-call wrapper, all tested (21 tests). Roadmap: whitespace/seed conditions surfaced as first-class Inspect conditions. Part of the [Open Evaluation Robustness Lab](https://manifund.org/projects/open-evaluation-robustness-lab--90-day-pilot).

## License

MIT. AI-assisted authorship disclosed in [`AI_USAGE.md`](AI_USAGE.md); all logic is deterministic and unit-tested.
