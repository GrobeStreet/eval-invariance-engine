# AI usage disclosure

Consistent with the `bobby-research-os` doctrine — *AI may propose; deterministic systems must verify* — this repository discloses its AI-assisted authorship.

- **AI-assisted:** initial scaffolding of modules, tests, and documentation.
- **Deterministically verified:** every claim the code makes is checked by the test suite (`tests/`), which asserts exact, hand-computed numbers for the perturbation logic and the drift/flip-rate statistics. The bootstrap is seed-fixed and reproducible. No result in this package depends on a model grading another model.
- **Human-owned:** method, thresholds, and interpretation.

Reproduce the verification:

```bash
python -m pytest -q
python examples/demo.py
```
