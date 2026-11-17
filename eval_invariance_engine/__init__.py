"""Descriptive paired correctness diagnostics under declared transformations.

Sensitivity does not by itself establish memorization or contamination.
"""
from .perturbations import MCQItem, cyclic_reorder, all_cyclic_variants, whitespace_variant
from .report import InvarianceReport, build_report
from .validation import results_from_rows

__version__ = "0.4.0"
__all__ = [
    "MCQItem", "cyclic_reorder", "all_cyclic_variants", "whitespace_variant",
    "InvarianceReport", "build_report", "results_from_rows",
]
