# Eval Invariance Engine

Measure **accuracy drift and per-item correctness changes** under declared
conditions. The core is standard-library Python; the optional Inspect adapter
builds a new plain-MCQ task using cyclic option rotations.

These diagnostics do not establish statistical equivalence, production
readiness, contamination, or memorization. Check that a transformation preserves
the intended answer for your task.

## Install from this checkout

```bash
python -m pip install -e .
invariance-check demo
```

Core: Python 3.9+. Optional integration: Python 3.11+ and Inspect AI 0.3.290 or
newer; 0.3.290 is the pinned integration-test version for this change.
The default branch or a pull request is not automatically a PyPI release.

## Preferred input: explicit item IDs

A JSON array contains exactly one row per item and condition. IDs and condition
names are non-empty strings; `correct` must be an actual JSON boolean.

```json
[
  {"item_id": "q1", "condition": "original", "correct": true},
  {"item_id": "q2", "condition": "original", "correct": false},
  {"item_id": "q2", "condition": "rotated", "correct": false},
  {"item_id": "q1", "condition": "rotated", "correct": true}
]
```

Rows may be shuffled. Duplicates, missing item/condition cells, empty data,
single conditions, and strings such as `"false"` are rejected.

```bash
invariance-check report examples/paired_results.json
invariance-check report examples/paired_results.json --json
invariance-check report results.json --threshold 0.05 --fail-on-drift
```

Exit codes: 0 = valid report without a triggered requested gate; 1 = observed
accuracy drift exceeds the requested tolerance; 2 = invalid input/settings.
The default tolerance is an illustrative 0.03, not a validated universal
readiness threshold. Select tolerances before inspecting results.
A drift-only gate does not gate correctness instability.

Legacy mappings such as `{"a": [true, false], "b": [false, true]}` require
`--assume-aligned` at the CLI. That flag explicitly trusts row positions; the
program cannot verify item identity in this format. Python mapping callers
likewise assert positional alignment. Prefer ID-bearing rows.

## Python

```python
from eval_invariance_engine import build_report

rows = [
    {"item_id": "q1", "condition": "a", "correct": True},
    {"item_id": "q1", "condition": "b", "correct": False},
    {"item_id": "q2", "condition": "a", "correct": False},
    {"item_id": "q2", "condition": "b", "correct": True},
]
report = build_report(rows, fragile_threshold=0.05, n_boot=2000, seed=0)
print(report.summary())
# Accuracy drift is zero, but correctness_flip_rate is 1.0.
```

The report names the point-estimate threshold result
`drift_above_threshold` or `drift_not_above_threshold`. Neither means invariant.
It includes per-condition accuracy, correctness flip rate, and an exploratory
paired-item percentile bootstrap interval for max accuracy drift, with seed,
draw count and method recorded. Resampling preserves the entire condition
vector for each original item.

The bootstrap assumes independent original items representative of a target
population. It does not justify population inference from a convenience sample.
Small samples, boundary estimates and max-over-condition selection can give
poor interval coverage. This implementation is not an equivalence test.

**Correctness flips are not answer flips.** Two different wrong answers do not
change correctness. Boolean correctness inputs cannot recover underlying-answer
changes. The deprecated `report.flip_rate` property aliases
`correctness_flip_rate` only.

## Inspect: deliberately build a new task

```bash
python -m pip install -e ".[inspect]"
```

```python
from inspect_ai import eval
from eval_invariance_engine.inspect_adapter import cyclic_mcq_task

audit = cyclic_mcq_task(my_task.dataset)
# Configure this new task's model, limits and other settings explicitly.
eval(audit, model="your-configured-model")
```

This is a **new generate-only audit**, not a general wrapper. Source solvers,
scorers, tools, sandbox, setup, model settings and limits are not inherited.
Only plain question/choices/single-target samples are supported. Non-MCQ,
chat/file-bearing, duplicate-ID and mixed-choice-count datasets fail explicitly.
Source sample metadata is retained except that reserved `invariance_` keys are
rejected. The scorer accepts a single option letter; other output is counted
incorrect and labeled as an invalid answer, not guessed from its first letter.

Native metrics are `invariance_drift` and
`invariance_correctness_flip_rate`. Both validate identity, duplicates and full
coverage; they do not silently discard missing conditions. Use one epoch and
complete rotations. Repeated epochs require a separately specified analysis.

The old `invariance_task(my_task)` entry point now errors rather than silently
replacing task semantics. Use the new factory, or explicitly acknowledge the
rebuild with `invariance_task(my_task, rebuild=True)`.
`invariance_flip_rate()` is a deprecated name for correctness flips.
`--fail-on-fragile` remains an alias for the drift-only CLI gate.

Cyclic rotations are not all permutations. Whitespace restyling remains a
separate utility and is not a generated Inspect condition.

## Validation and worked report

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python examples/demo.py
```

The core tests cover invalid inputs and order-independent pairing. Optional
tests exercise native Inspect metrics and a complete evaluation with its
built-in mock provider, without provider keys or inference charges.
See [the worked report](examples/WORKED_REPORT.md).

MIT. AI-assisted authorship is disclosed in [AI_USAGE.md](AI_USAGE.md).
