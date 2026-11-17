# Worked report: identical accuracy can hide unstable decisions

This is a four-item synthetic example, not a model experiment or an
independent validation result. The second condition deliberately arrives in
a different row order. Item IDs establish pairing.

Run from a source installation:

```bash
invariance-check report examples/paired_results.json --json
```

| Item | Original | Rotated |
|---|---|---|
| q1 | Correct | Incorrect |
| q2 | Incorrect | Correct |
| q3 | Correct | Correct |
| q4 | Incorrect | Incorrect |

Both conditions are 2/4 correct (50%). Observed accuracy drift is **0 percentage
points**. Correctness changes for 2/4 original items (**50%**).

The output says `drift_not_above_threshold` against the illustrative 3-point
tolerance. It does not say the behavior is invariant or ready to deploy. A
drift-only CI gate would pass this input; a decision that needs stable item-level
behavior must consider correctness instability separately.

The paired-item bootstrap interval in the generated JSON is exploratory and
uses 2,000 resamples with seed 0. Four synthetic items do not support a
population reliability conclusion. The file records correctness only, so an
underlying-answer flip rate is **not measured**.

Machine-readable output is committed as [paired_report.json](paired_report.json).
