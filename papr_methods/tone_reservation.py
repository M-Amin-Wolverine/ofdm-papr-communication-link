"""
PAPR Method: Tone Reservation (TR)
==================================

Tone Reservation (TR) is reserved for Phase-2 implementation.

Current status
--------------
Tone Reservation is intentionally NOT implemented in Stage-1.

Current Stage-1 methods:

    NONE
        Locked scientific reference.

    CLIPPING
        Implemented amplitude-clipping method.

Tone Reservation remains a formal placeholder so that the method registry,
experiment configuration, and future PAPR pipeline are prepared in advance.

Tone Reservation principle
---------------------------
Tone Reservation reserves a subset of OFDM subcarriers exclusively for
PAPR reduction.

The reserved subcarriers do not carry information data. Instead, their
complex-valued coefficients are optimized to generate a time-domain
cancellation signal.

Conceptually:

        Frequency-domain OFDM symbol
                    │
             ┌──────┴──────┐
             │             │
             ▼             ▼
        Data tones    Reserved tones
             │             │
             │        optimization
             │             │
             └──────┬──────┘
                    ▼
                  IFFT
                    │
                    ▼
             Time-domain OFDM
                    │
                    ▼
              Peak reduction

The data-bearing subcarriers remain unchanged.

The optimization modifies only the reserved tones.

Mathematically, the transmitted frequency-domain vector can be represented
conceptually as:

    X_TR = X_data + C_reserved

where:

    X_data
        contains the original data-bearing subcarriers.

    C_reserved
        contains the optimized cancellation coefficients on reserved tones.

The resulting time-domain waveform is then:

    x_TR = IFFT(X_TR)

and its PAPR is evaluated according to the project-wide PAPR definition.

Planned Phase-2 parameters
--------------------------

reserved_indices : array-like of int
    FFT-bin indices assigned to PAPR-reduction tones.

n_iterations : int
    Maximum number of iterative optimization steps.

target_papr_db : float, optional
    Optional early-stopping PAPR target.

step_size : float
    Planned optimization/update step size.

max_reserved_power : float, optional
    Optional power constraint on the reserved-tone cancellation signal.

optimization_method : str
    Planned optimization strategy.

Possible future approaches include:

    - iterative clipping / filtering inspired optimization;
    - gradient-based optimization;
    - kernel-based peak cancellation;
    - constrained least-squares optimization.

Scientific considerations
--------------------------
A complete Tone Reservation implementation should evaluate:

    - PAPR reduction;
    - number of reserved subcarriers;
    - reserved-tone placement;
    - cancellation-signal power;
    - spectral efficiency;
    - data-rate loss;
    - convergence;
    - iteration count;
    - computational complexity;
    - oversampling;
    - BER;
    - EVM;
    - PSD;
    - modulation order;
    - channel conditions.

Important distinction
---------------------
Tone Reservation does NOT modify the original data symbols.

Instead:

    data subcarriers
        ↓
    remain unchanged

while:

    reserved subcarriers
        ↓
    are optimized for peak cancellation.

This distinguishes TR from ACE and PTS.

Stage-1 behavior
----------------
This module intentionally raises ``NotImplementedError``.

It must NOT silently fall back to NONE or CLIPPING.

If an experiment requests Tone Reservation before Phase-2 is implemented,
the simulator must explicitly report that the requested method is
unavailable.

Future interface
----------------
The public API is reserved:

    apply_tone_reservation(...)
    process(...)

When Phase-2 implementation begins, these functions should return the
same common ``PAPRProcessResult`` structure used by the other PAPR methods.
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

METHOD = PAPRMethod.TONE_RESERVATION

METHOD_NAME = METHOD.value

IMPLEMENTED = False

STAGE = "Phase-2"


# ============================================================================
# Core processing API
# ============================================================================


def apply_tone_reservation(
    *args: Any,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> None:
    """
    Placeholder for the future Tone Reservation implementation.

    Tone Reservation is intentionally unavailable during Stage-1.

    Parameters
    ----------
    *args:
        Reserved for future waveform/frequency-domain processing.

    rng:
        Optional random generator reserved for future stochastic
        optimization, if required.

    **kwargs:
        Reserved for future Tone Reservation configuration.

    Raises
    ------
    NotImplementedError
        Always, while Tone Reservation remains a Phase-2 feature.
    """

    raise NotImplementedError(
        "Tone Reservation (TR) is not implemented yet. "
        "Tone Reservation is scheduled for Phase-2. "
        "Use 'none' or 'clipping' for the current Stage-1 experiments."
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Pipeline-facing Tone Reservation entry point.

    Tone Reservation is currently unavailable in Stage-1.

    The explicit ``TransmitFrame`` interface is retained so the future
    implementation can be inserted into the same pipeline as the other
    PAPR methods.
    """

    if not isinstance(transmit_frame, TransmitFrame):
        raise TypeError(
            "process() requires a TransmitFrame."
        )

    raise NotImplementedError(
        "Tone Reservation (TR) is not implemented in the current stage. "
        f"Requested method={PAPRMethod.TONE_RESERVATION.value!r}. "
        "Tone Reservation is reserved for Phase-2."
    )


# ============================================================================
# Method information
# ============================================================================


def method_name() -> str:
    """
    Return the canonical Tone Reservation method name.
    """

    return METHOD_NAME


def is_implemented() -> bool:
    """
    Return False because Tone Reservation is currently a Phase-2 stub.
    """

    return IMPLEMENTED


def stage() -> str:
    """
    Return the planned implementation stage.
    """

    return STAGE


def description() -> str:
    """
    Return a human-readable Tone Reservation description.
    """

    return (
        "Tone Reservation (TR): reserves selected OFDM subcarriers "
        "for peak-cancellation signal optimization while leaving "
        "data-bearing subcarriers unchanged. Implementation is "
        "reserved for Phase-2."
    )


def metadata() -> dict[str, Any]:
    """
    Return static metadata describing Tone Reservation.
    """

    return {
        "name": METHOD_NAME,
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "algorithm": "Tone Reservation",
        "modifies_waveform": True,
        "frequency_domain_processing": True,
        "data_subcarriers_modified": False,
        "reserved_subcarriers_required": True,
        "requires_side_information": False,
        "randomness": False,
        "description": description(),
    }


# ============================================================================
# Compatibility aliases
# ============================================================================

tone_reservation = process

tr = process


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "METHOD",
    "METHOD_NAME",
    "IMPLEMENTED",
    "STAGE",
    "apply_tone_reservation",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "tone_reservation",
    "tr",
]
