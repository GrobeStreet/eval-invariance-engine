# eval-invariance-engine

A small, standard-library diagnostic for evaluation sensitivity to declared
meaning-preserving changes, with an experimental Inspect AI adapter.
It generalizes the option-order diagnostic in
[mmlu-robustness-audit](https://github.com/GrobeStreet/mmlu-robustness-audit).

This does **not** establish contamination, memorization, production readiness,
or a causal explanation for score changes. Verify that each transformation
actually preserves meaning: whitespace matters in code and some options refer
to labels or ordering (for example, "all of the above"). Cyclic rotations are
not an exhaustive test of all permutations.

## Source hardening status

This source revision hardens the core and CLI. **No new PyPI release is implied.**
The optional Inspect adapter is not fully validated; see limitations below.

## CLI

```bash
invariance-check demo
invariance-check report results.json
invariance-check report results.json --fail-on-fragile
```

Prefer explicit item IDs:

```json
[
  {"item_id": "q1", "condition": "original", "correct": true},
  {"item_id": "q2", "condition": "original", "correct": false},
  {"item_id": "q2", "condition": "rotated", "correct": true},
  {"item_id": "q1", "condition": "rotated", "correct": false}
]
```

Rows are aligned by item identity, not arrival order. Every item must occur
exactly once under each condition. Duplicate pairs, unequal coverage, missing
IDs, and strings such as `"false"` are rejected. Use actual JSON booleans.

Legacy mappings such as `{"a": [true, false], "b": [false, true]}` have no
identities to check. They require `--assume-aligned`, an explicit assertion
that you have verified pairing yourself. Never use it to bypass missing data.

`--fail-on-fragile` exits 1 when observed aggregate drift exceeds `--threshold`
(default 0.03); invalid inputs exit 2. Exit 0 is **not** a reliability certificate.
The gate is drift-only: inspect correctness flips and task-specific risks too.

## Python API

```python
from eval_invariance_engine.report import build_report, results_from_rows

rows = [
    {"item_id": "q1", "condition": "a", "correct": True},
    {"item_id": "q1", "condition": "b", "correct": False},
    {"item_id": "q2", "condition": "a", "correct": False},
    {"item_id": "q2", "condition": "b", "correct": True},
]
report = build_report(results_from_rows(rows))
print(report.summary())
# Aggregate drift is 0, while correctness flip_rate is 1.0.
# BELOW_THRESHOLD describes drift only, NOT invariant per-item behavior.
```

The low-level `build_report(mapping)` still accepts already position-aligned
boolean arrays. Its caller is responsible for matching item identities.

## Interpretation and migration

- At least two conditions and one paired item are required. Empty or
  single-condition comparisons fail rather than reporting success.
- `fragile` means the observed aggregate drift exceeds the chosen threshold.
- The former `invariant` verdict is now `below_threshold`. Update consumers
  comparing that string. Neither label is a hypothesis test or equivalence test.
- `flip_rate` measures changes in **correctness**, not all changes in the
  underlying answer. Switching between two wrong answers is not captured.
- The paired bootstrap resamples the same item indices across conditions.
  Its empirical percentile interval assumes independently sampled items;
  clustered cases require a different resampling design. Small/uniform samples
  can produce misleadingly narrow or degenerate intervals. The interval is not
  a guarantee of population coverage and not a proof of invariance.

## Experimental Inspect adapter: known limitations

`invariance_task()` constructs a new task with `solver=generate()`. It does not
preserve an arbitrary base task's solver, system context, sandbox, tools, or
other configuration. Non-MCQ samples are **skipped**, not passed through.
Use only as a distinct, documented MCQ experiment, not a transparent wrapper.
The native metrics also need stronger incomplete-group and score-parsing checks.

The legacy `invariance_report_from_scores()` helper still groups rows by arrival
order and coerces correctness values. **Do not use it on unvalidated inputs.**
For final reports use `results_from_rows()` with explicit `item_id` values and
strict booleans, followed by `build_report()` instead. Fixing and validating the
full optional adapter is a separate review task; this patch does not claim it
is production-ready.

## Tests and review

Run `python -m pytest -q` in an environment with the repository's development
dependencies. Core-only checks can run without Inspect AI. This change adds
input-safety regression tests and updates the CLI/report tests for the migration.
Local verification ran 71 core regression tests; the optional Inspect integration
and real-model experiments were not run in that verification environment.

Outside feedback is welcome in
[issue #1](https://github.com/GrobeStreet/eval-invariance-engine/issues/1).
AI-assisted implementation and testing are disclosed; this is not independent
human peer review. No claim of originality for option-order sensitivity is made.

## License

MIT. See [AI_USAGE.md](AI_USAGE.md) for the existing authorship disclosure.
