"""
PAPR Method: Active Constellation Extension (ACE)
==================================================

Active Constellation Extension (ACE) is reserved for Phase-2
implementation.

Current status
--------------
ACE is intentionally NOT implemented in Stage-1.

Current Stage-1 methods:

    NONE
        Locked scientific reference.

    CLIPPING
        Implemented amplitude-clipping method.

ACE remains a formal placeholder so that the PAPR method architecture,
registry, experiment configuration, and future pipeline integration are
already prepared.

ACE principle
-------------
Active Constellation Extension reduces OFDM time-domain peaks by modifying
selected constellation points within their allowed decision regions.

Unlike conventional clipping, ACE does not simply truncate the time-domain
waveform.

Instead, selected frequency-domain constellation symbols are moved outward
within permissible regions.

Conceptually:

    Original constellation
             │
             ▼
    Identify extendable points
             │
             ▼
    Determine allowed extension
             │
             ▼
    Modify constellation
             │
             ▼
           IFFT
             │
             ▼
       Time-domain OFDM
             │
             ▼
            PAPR

The modified constellation must remain decodable according to the
corresponding decision-region constraints.

Planned Phase-2 parameters
--------------------------

n_iterations : int
    Number of iterative ACE optimization/projection steps.

max_extension : float
    Maximum allowed extension relative to the nominal constellation
    amplitude/energy.

modulation : ModulationType
    Constellation used by the OFDM system.

step_size : float
    Planned optimization step size for iterative extension.

optimization_method : str
    Planned optimization strategy.

Possible future approaches include:

    - projection;
    - iterative clipping/filtering-inspired optimization;
    - gradient-based optimization;
    - constrained peak minimization.

oversampling : int
    PAPR evaluation should use the project's configured oversampling factor.

Scientific considerations
--------------------------
A complete ACE implementation should evaluate:

    - PAPR reduction;
    - BER;
    - EVM;
    - constellation displacement;
    - minimum decision distance;
    - maximum constellation extension;
    - modulation order;
    - optimization iterations;
    - computational complexity;
    - convergence behavior;
    - spectral effects;
    - oversampling;
    - interaction with channel impairments.

Important distinction
---------------------
ACE differs fundamentally from hard clipping.

Hard clipping:

    time domain
        ↓
    truncate amplitude peaks

ACE:

    frequency domain
        ↓
    modify allowed constellation points
        ↓
    IFFT
        ↓
    reduced time-domain peaks

Therefore ACE should eventually be implemented at the appropriate
frequency-domain processing stage rather than by reusing the clipping
implementation.

Stage-1 behavior
----------------
This module intentionally raises ``NotImplementedError``.

It must NOT silently fall back to NONE or CLIPPING.

If an experiment explicitly requests ACE, the simulator must report that
ACE is unavailable rather than producing results using another algorithm.

Future interface
----------------
The public API is reserved:

    apply_ace(...)
    process(...)

When ACE is implemented, the method should return the same common
``PAPRProcessResult`` structure used by the other PAPR algorithms.
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

METHOD = PAPRMethod.ACE

METHOD_NAME = METHOD.value

IMPLEMENTED = False

STAGE = "Phase-2"


# ============================================================================
# Core processing API
# ============================================================================


def apply_ace(
    *args: Any,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> None:
    """
    Placeholder for the future ACE implementation.

    ACE is intentionally unavailable during Stage-1.

    Parameters
    ----------
    *args:
        Reserved for future ACE waveform/frequency-domain processing.

    rng:
        Optional random generator reserved for future stochastic
        optimization, if required.

    **kwargs:
        Reserved for future ACE configuration parameters.

    Raises
    ------
    NotImplementedError
        Always, while ACE remains a Phase-2 feature.
    """

    raise NotImplementedError(
        "Active Constellation Extension (ACE) is not implemented yet. "
        "ACE is scheduled for Phase-2. "
        "Use 'none' or 'clipping' for the current Stage-1 experiments."
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Pipeline-facing ACE entry point.

    ACE is currently unavailable in Stage-1.

    The explicit ``TransmitFrame`` interface is reserved for compatibility
    with the future PAPR processing pipeline.
    """

    if not isinstance(transmit_frame, TransmitFrame):
        raise TypeError(
            "process() requires a TransmitFrame."
        )

    raise NotImplementedError(
        "Active Constellation Extension (ACE) is not implemented in "
        "the current stage. "
        f"Requested method={PAPRMethod.ACE.value!r}. "
        "ACE is reserved for Phase-2."
    )


# ============================================================================
# Method information
# ============================================================================


def method_name() -> str:
    """
    Return the canonical ACE method name.
    """

    return METHOD_NAME


def is_implemented() -> bool:
    """
    Return False because ACE is currently a Phase-2 stub.
    """

    return IMPLEMENTED


def stage() -> str:
    """
    Return the planned implementation stage.
    """

    return STAGE


def description() -> str:
    """
    Return a human-readable ACE description.
    """

    return (
        "Active Constellation Extension (ACE): modifies allowed "
        "constellation points to reduce time-domain OFDM peaks. "
        "Implementation is reserved for Phase-2."
    )


def metadata() -> dict[str, Any]:
    """
    Return static metadata describing the ACE method.
    """

    return {
        "name": METHOD_NAME,
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "algorithm": "Active Constellation Extension",
        "modifies_waveform": True,
        "frequency_domain_processing": True,
        "requires_constellation_constraints": True,
        "requires_side_information": False,
        "randomness": False,
        "description": description(),
    }


# ============================================================================
# Compatibility alias
# ============================================================================

ace = process


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "METHOD",
    "METHOD_NAME",
    "IMPLEMENTED",
    "STAGE",
    "apply_ace",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "ace",
]
