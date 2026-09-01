"""
PAPR Method: Selected Mapping (SLM)
===================================

Selected Mapping (SLM) is reserved for Phase-2 implementation.

Current status
--------------
SLM is intentionally NOT implemented in Stage-1.

The current project baseline consists of:

    PAPRMethod.NONE
        ↓
    Reference / unprocessed OFDM waveform

and:

    PAPRMethod.CLIPPING
        ↓
    Amplitude clipping

SLM will be implemented in a later phase without changing the public
registry/pipeline interface.

Planned SLM principle
---------------------
For an OFDM frequency-domain symbol X:

    1. Generate multiple candidate phase sequences.
    2. Multiply X by each phase sequence.
    3. Transform each candidate to the time domain.
    4. Measure candidate PAPR.
    5. Select the candidate with minimum PAPR.
    6. Preserve the required side-information for receiver recovery.

Conceptually:

        X
        │
        ├── × B₁ ── IFFT ── PAPR₁ ──┐
        ├── × B₂ ── IFFT ── PAPR₂ ──┤
        ├── × B₃ ── IFFT ── PAPR₃ ──┤──→ minimum PAPR
        │                            │
        └── × Bᵥ ── IFFT ── PAPRᵥ ──┘

Phase-2 considerations
----------------------
A complete implementation should eventually define:

    - number of SLM candidates;
    - phase-factor set;
    - deterministic/random phase generation;
    - RNG handling;
    - candidate generation;
    - PAPR evaluation;
    - candidate selection;
    - side-information representation;
    - receiver-side recovery;
    - computational complexity;
    - reproducibility;
    - compatibility with oversampling;
    - compatibility with CP insertion;
    - BER/EVM impact;
    - metadata reporting.

Important
---------
This module intentionally raises ``NotImplementedError``.

Do NOT silently fall back to NONE or clipping when SLM is requested.
Such fallback would produce scientifically invalid experiments because the
experiment configuration would claim SLM while the simulator actually ran
another algorithm.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from ofdm_linksim.core.types import (
    PAPRMethod,
    PAPRResult,
    TransmitFrame,
)


# ============================================================================
# Method constants
# ============================================================================

METHOD = PAPRMethod.SLM

METHOD_NAME = METHOD.value

IMPLEMENTED = False

STAGE = "Phase-2"


# ============================================================================
# Public processing API
# ============================================================================


def apply_slm(
    *args: Any,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> None:
    """
    Placeholder for the future SLM waveform-processing implementation.

    Status
    ------
    NOT IMPLEMENTED.

    This function deliberately raises ``NotImplementedError`` rather than
    falling back to another PAPR method.
    """

    raise NotImplementedError(
        "Selected Mapping (SLM) is not implemented yet. "
        "SLM is scheduled for Phase-2. "
        "Use 'none' or 'clipping' for the current Stage-1 experiments."
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Pipeline-facing SLM entry point.

    Status
    ------
    NOT IMPLEMENTED.

    This function exists so that the public interface is reserved now and
    can be implemented later without changing the pipeline API.
    """

    if not isinstance(transmit_frame, TransmitFrame):
        raise TypeError(
            "process() requires a TransmitFrame."
        )

    raise NotImplementedError(
        "Selected Mapping (SLM) is not implemented in the current stage. "
        "SLM is reserved for Phase-2."
    )


# ============================================================================
# Method information
# ============================================================================


def method_name() -> str:
    """Return the canonical SLM method name."""

    return METHOD_NAME


def is_implemented() -> bool:
    """Return False because SLM is currently a Phase-2 stub."""

    return IMPLEMENTED


def stage() -> str:
    """Return the planned implementation stage."""

    return STAGE


def description() -> str:
    """Return a human-readable description of SLM."""

    return (
        "Selected Mapping (SLM): generates multiple phase-rotated "
        "OFDM candidates and selects the candidate with minimum PAPR. "
        "Implementation is reserved for Phase-2."
    )


def metadata() -> dict[str, Any]:
    """
    Return static metadata for the SLM method.
    """

    return {
        "name": METHOD_NAME,
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "algorithm": "Selected Mapping",
        "modifies_waveform": True,
        "requires_side_information": True,
        "randomness": True,
        "description": description(),
    }


# ============================================================================
# Compatibility aliases
# ============================================================================

slm = process


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "METHOD",
    "METHOD_NAME",
    "IMPLEMENTED",
    "STAGE",
    "apply_slm",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "slm",
]

