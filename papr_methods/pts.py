```python
"""
PAPR Method: Partial Transmit Sequence (PTS)
=============================================

Partial Transmit Sequence (PTS) is reserved for Phase-2 implementation.

Current status
--------------
PTS is intentionally NOT implemented in Stage-1.

The current Stage-1 PAPR methods are:

    NONE
        Locked scientific reference.

    CLIPPING
        Implemented amplitude-clipping method.

PTS is kept as a formal placeholder so that the package architecture,
method registry, experiment configuration, and future receiver-side
processing can be prepared without changing the public API later.

PTS principle
-------------
Partial Transmit Sequence operates in the frequency domain.

Given an OFDM frequency-domain symbol:

    X = [X_0, X_1, ..., X_{N-1}]

the active subcarriers are partitioned into V disjoint sub-blocks:

    X = X^(1) + X^(2) + ... + X^(V)

Each sub-block is multiplied by a phase factor:

    b_v ∈ B

where B is the allowed phase-factor set.

A candidate transmitted symbol is then:

    X' = Σ b_v X^(v)

After IFFT:

    x' = IFFT{X'}

the PAPR of the candidate is evaluated.

The phase-vector combination producing the minimum PAPR is selected.

Conceptually:

        Frequency-domain OFDM symbol
                    │
                    ▼
             ┌─────────────┐
             │ Partition   │
             │ into V      │
             │ sub-blocks  │
             └──────┬──────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
         X¹        X²       Xᵛ
          │         │         │
          ×b₁       ×b₂      ×bᵥ
          │         │         │
          └─────────┼─────────┘
                    │
                    ▼
                 Combine
                    │
                    ▼
                   IFFT
                    │
                    ▼
               Candidate x'
                    │
                    ▼
                  PAPR
                    │
                    ▼
             Minimum-PAPR
               selection

Planned Phase-2 parameters
--------------------------
n_subblocks : int
    Number of frequency-domain sub-blocks.

n_candidates : int
    Number of phase-vector candidates evaluated.

phase_set : sequence of float or complex
    Allowed phase rotations.

Typical phase sets include:

    {0, π}

or:

    {0, π/2, π, 3π/2}

partition_scheme : str
    Planned partitioning strategy.

Possible future strategies include:

    - adjacent
    - interleaved
    - pseudo-random

oversampling : int
    PAPR candidates should be evaluated using the project's configured
    oversampling factor.

side_information : bool
    PTS generally requires the receiver to know the selected phase-vector
    combination unless a side-information-free recovery mechanism is used.

Scientific considerations
--------------------------
A complete PTS implementation should evaluate:

    - PAPR reduction;
    - number of sub-blocks;
    - number of phase candidates;
    - search complexity;
    - exhaustive versus iterative optimization;
    - oversampling;
    - modulation order;
    - active subcarrier allocation;
    - side-information overhead;
    - BER impact;
    - EVM;
    - computational complexity;
    - reproducibility.

The implementation must use the same PAPR definition as the rest of the
project:

    PAPR = max(|x[n]|²) / mean(|x[n]|²)

with PAPR evaluated on useful OFDM samples according to the project
contract.

Stage-1 behavior
----------------
This module intentionally raises ``NotImplementedError``.

It must NOT silently fall back to:

    NONE

or:

    CLIPPING

Doing so would make an experiment configured for PTS execute another
algorithm and would invalidate the resulting scientific comparison.

Future compatibility
--------------------
The public interface is reserved now:

    apply_pts(...)
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

METHOD = PAPRMethod.PTS

METHOD_NAME = METHOD.value

IMPLEMENTED = False

STAGE = "Phase-2"


# ============================================================================
# Core processing API
# ============================================================================


def apply_pts(
    *args: Any,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> None:
    """
    Placeholder for the future PTS implementation.

    Parameters
    ----------
    *args:
        Reserved for the future waveform/frequency-domain input interface.

    rng:
        Optional random generator reserved for future randomized partitioning
        or candidate generation.

    **kwargs:
        Reserved for future PTS configuration parameters.

    Raises
    ------
    NotImplementedError
        Always, while PTS remains a Phase-2 feature.
    """

    raise NotImplementedError(
        "Partial Transmit Sequence (PTS) is not implemented yet. "
        "PTS is scheduled for Phase-2. "
        "Use 'none' or 'clipping' for the current Stage-1 experiments."
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Pipeline-facing PTS entry point.

    PTS is currently unavailable in Stage-1.

    The explicit ``TransmitFrame`` type is retained so that the future
    implementation can be plugged into the same pipeline interface as
    NONE, CLIPPING, SLM, Tone Reservation, and ACE.
    """

    if not isinstance(transmit_frame, TransmitFrame):
        raise TypeError(
            "process() requires a TransmitFrame."
        )

    raise NotImplementedError(
        "Partial Transmit Sequence (PTS) is not implemented in the "
        "current stage. "
        f"Requested method={PAPRMethod.PTS.value!r}. "
        "PTS is reserved for Phase-2."
    )


# ============================================================================
# Method information
# ============================================================================


def method_name() -> str:
    """
    Return the canonical PTS method name.
    """

    return METHOD_NAME


def is_implemented() -> bool:
    """
    Return False because PTS is currently a Phase-2 stub.
    """

    return IMPLEMENTED


def stage() -> str:
    """
    Return the planned implementation stage.
    """

    return STAGE


def description() -> str:
    """
    Return a human-readable PTS description.
    """

    return (
        "Partial Transmit Sequence (PTS): partitions the frequency-domain "
        "OFDM symbol into sub-blocks, applies candidate phase rotations, "
        "and selects the minimum-PAPR combination. Implementation is "
        "reserved for Phase-2."
    )


def metadata() -> dict[str, Any]:
    """
    Return static metadata describing the PTS method.
    """

    return {
        "name": METHOD_NAME,
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "algorithm": "Partial Transmit Sequence",
        "modifies_waveform": True,
        "requires_side_information": True,
        "randomness": False,
        "frequency_domain_processing": True,
        "description": description(),
    }


# ============================================================================
# Compatibility alias
# ============================================================================

pts = process


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "METHOD",
    "METHOD_NAME",
    "IMPLEMENTED",
    "STAGE",
    "apply_pts",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "pts",
]
```
