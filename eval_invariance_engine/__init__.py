"""eval-invariance-engine — measure whether an eval score survives non-semantic perturbation.

A benchmark score that moves when you cyclically reorder the answer options, jitter the
whitespace, or change the seed is measuring formatting-sensitivity and memorization, not
reasoning. This package quantifies that drift and ships a drop-in adapter for the Inspect
AI evaluation harness.

Core (framework-agnostic, dependency-light): `perturbations`, `report`.
Integration: `inspect_adapter` (optional; requires `inspect_ai`) — incl. `invariance_task()`.
CLI: `invariance-check` (see `cli`).
"""
from .perturbations import MCQItem, cyclic_reorder, all_cyclic_variants, whitespace_variant
from .report import InvarianceReport, build_report

__version__ = "0.3.0"
__all__ = [
    "MCQItem",
    "cyclic_reorder",
    "all_cyclic_variants",
    "whitespace_variant",
    "InvarianceReport",
    "build_report",
]
