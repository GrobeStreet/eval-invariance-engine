"""Runnable demo: a 'brittle' model that reads the label instead of reasoning.

We simulate a model that always answers 'A' (a memorized position bias). Under
cyclic option reordering the *correct* letter moves, so this model's accuracy
swings wildly across conditions — exactly the fragility the engine is built to
expose. No API key or network required.
"""
from eval_invariance_engine.perturbations import MCQItem, all_cyclic_variants
from eval_invariance_engine.report import build_report

ITEMS = [
    MCQItem("2+2=?", ["4", "5", "6", "7"], 0),
    MCQItem("Capital of France?", ["Paris", "Rome", "Bonn", "Madrid"], 0),
    MCQItem("H2O is?", ["Water", "Gold", "Salt", "Iron"], 0),
    MCQItem("Largest planet?", ["Jupiter", "Mars", "Venus", "Mercury"], 0),
]

LETTERS = "ABCD"


def brittle_model_always_picks_A(_rendered_options):
    return 0  # always selects the first listed option


def main():
    results = {f"shift{s}": [] for s in range(4)}
    for item in ITEMS:
        for shift, variant in enumerate(all_cyclic_variants(item)):
            pred = brittle_model_always_picks_A(variant.options)
            results[f"shift{shift}"].append(pred == variant.answer_index)
    report = build_report(results, seed=0)
    print(report.summary())
    print("verdict:", report.verdict)


if __name__ == "__main__":
    main()
