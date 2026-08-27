# eval-invariance-engine

**A benchmark score that moves when you cyclically reorder the answer options, jitter the whitespace, or change the seed is not measuring reasoning — it is measuring formatting-sensitivity and memorization.** This library quantifies that drift and ships a drop-in adapter for [Inspect AI](https://inspect.aisi.org.uk), the evaluation harness standardizing across AI-safety work.

It generalizes the option-order robustness method from [`mmlu-robustness-audit`](https://github.com/GrobeStreet/mmlu-robustness-audit) into a reusable, framework-agnostic tool with a first-class Inspect integration.

## Why

Leaderboards treat a headline score as ground truth. But the same model, on the same questions, can score several points differently when you change things that carry no meaning. If a score is not *invariant* to non-semantic perturbation, the ranking it produces is partly an artifact. This engine makes that fragility measurable — and re-runnable.

## Install

```bash
pip install eval-invariance-engine          # core, zero dependencies
pip install "eval-invariance-engine[inspect]"  # + Inspect AI integration
```

## Quickstart (framework-agnostic)

```python
from eval_invariance_engine import MCQItem, all_cyclic_variants, build_report

item = MCQItem("Capital of France?", ["Paris", "Rome", "Bonn", "Madrid"], answer_index=0)

# score your model under every cyclic option ordering, item-aligned per condition
results = {"shift0": [...], "shift1": [...], "shift2": [...], "shift3": [...]}  # bool per item
report = build_report(results)
print(report.summary())
# [FRAGILE] n=... | drift=0.180 (95% CI 0.090-0.270) | flip_rate=0.31 | shift0=..., ...
```

Run the included demo (a memorized position-bias model, no API needed):

```bash
python examples/demo.py
```

## Inspect AI integration

```python
from inspect_ai import Task, eval
from inspect_ai.solver import generate
from inspect_ai.dataset import MemoryDataset
from eval_invariance_engine import MCQItem
from eval_invariance_engine.inspect_adapter import cyclic_variant_samples, invariance_scorer, invariance_report_from_scores

items = [MCQItem("2+2=?", ["4", "5", "6", "7"], 0)]
samples = [s for i, it in enumerate(items) for s in cyclic_variant_samples(it, group_id=str(i))]

task = Task(dataset=MemoryDataset(samples), solver=generate(), scorer=invariance_scorer())
logs = eval(task, model="openai/gpt-4o-mini")

scored = [{"condition": s.scores["_factory"].metadata["invariance_condition"],
           "correct": s.scores["_factory"].metadata["correct"]}
          for s in logs[0].samples]
print(invariance_report_from_scores(scored).summary())
```

## Method

- **Perturbations** are deterministic and semantics-preserving: cyclic option reordering (the answer set is identical, only labels rotate) and whitespace restyling. The correct real-world answer never changes.
- **Report**: per-condition accuracy, `max_drift` (best - worst condition), `flip_rate` (fraction of items whose correctness flipped across conditions — the sharpest non-semantic-sensitivity signal), a bootstrap 95% CI on the drift, and a `fragile` / `invariant` verdict.
- **Deterministic** given a seed; the core is pure standard library.

## Status

`v0.1.0` — core + Inspect adapter, tested. Roadmap: whitespace/seed conditions surfaced through the Inspect metric API, a CLI (`invariance-check <task>`), and a native custom `@metric`. Part of the [Open Evaluation Robustness Lab](https://manifund.org/projects/open-evaluation-robustness-lab--90-day-pilot).

## License

MIT. AI-assisted authorship disclosed in [`AI_USAGE.md`](AI_USAGE.md); all logic is deterministic and unit-tested.
