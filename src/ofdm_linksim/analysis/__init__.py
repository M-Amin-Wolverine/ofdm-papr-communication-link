"""
Analysis package – performance metrics for OFDM-PAPR-LinkSim
============================================================

Public measurement functions that produce the frozen result
containers defined in ``core.types``.
"""

from __future__ import annotations

from .ber import compute_ber, aggregate_ber
from .evm import compute_evm
from .ccdf import compute_ccdf, ccdf_at_probabilities
from .psd import compute_psd

__all__ = [
    "compute_ber",
    "aggregate_ber",
    "compute_evm",
    "compute_ccdf",
    "ccdf_at_probabilities",
    "compute_psd",
]
