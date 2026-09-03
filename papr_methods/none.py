"""
PAPR Method: NONE — Scientific Reference Baseline
===================================================

This module implements the ``NONE`` PAPR method.

The NONE method is the identity/reference processor:

    input waveform
          │
          ▼
    no modification
          │
          ▼
    PAPR measurement
          │
          ▼
    PAPRResult

No clipping, phase rotation, subcarrier reservation, constellation
extension, or other peak-reduction operation is performed.

Scientific role
---------------
NONE is the locked Stage-1 reference of OFDM-LinkSim.

Every PAPR-reduction algorithm must ultimately be evaluated relative to
this reference under otherwise identical simulation conditions.

For example:

    NONE → baseline PAPR
    CLIPPING → reduced PAPR + possible BER/EVM degradation
    SLM → reduced PAPR + side-information considerations
    PTS → reduced PAPR + optimization complexity
    Tone Reservation → reduced PAPR + spectral efficiency trade-off
    ACE → reduced PAPR + constellation modification

PAPR measurement
----------------
PAPR is measured only on the useful OFDM samples.

The cyclic prefix (CP) is excluded whenever an ``OFDMSignal`` or
``TransmitFrame`` is supplied.

For a useful discrete-time OFDM waveform x[n]:

    PAPR = max(|x[n]|²) / mean(|x[n]|²)

The exact numerical representation and validation of the metric are
delegated to ``make_papr_result()``.

Supported input types
---------------------
``apply_none()`` accepts:

    - TransmitFrame
    - OFDMSignal
    - ComplexArray / NumPy complex array

``process()`` is the pipeline-facing interface and accepts a
``TransmitFrame``.

Determinism
-----------
The NONE method does not use randomness.

The ``rng`` parameter is accepted solely for compatibility with the
common PAPR-method interface.

The input waveform is never modified in-place.

Scientific invariants
---------------------
The implementation guarantees:

    1. waveform samples are unchanged;
    2. no random processing occurs;
    3. PAPR is evaluated on useful samples;
    4. the returned waveform is an independent copy;
    5. CP exclusion is explicitly recorded in metadata;
    6. the reported method is PAPRMethod.NONE;
    7. the baseline cannot accidentally become another PAPR algorithm.

Compatibility
-------------
The module exposes:

    apply_none()
    process()
    none
    identity
    PAPRProcessResult

The ``process()`` function returns only ``PAPRResult`` because this is the
interface expected by the current pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    OFDMSignal,
    PAPRMethod,
    PAPRResult,
    TransmitFrame,
    make_papr_result,
    validate_complex_signal,
)

from ofdm_linksim.papr import get_useful_samples


# ============================================================================
# Constants
# ============================================================================

METHOD = PAPRMethod.NONE

METHOD_NAME = METHOD.value

IS_BASELINE = True

CP_EXCLUDED = True


# ============================================================================
# Result type
# ============================================================================


@dataclass(slots=True)
class PAPRProcessResult:
    """
    Common result container for a PAPR processing operation.

    Parameters
    ----------
    waveform:
        Output waveform.

        For NONE this is always an unchanged copy of the input waveform.

    papr:
        Computed PAPR metric.

    method:
        PAPR algorithm identifier.

    meta:
        Additional diagnostic information.
    """

    waveform: ComplexArray
    papr: PAPRResult
    method: PAPRMethod
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate the result immediately after construction.
        """

        validate_complex_signal(self.waveform)

        if not isinstance(self.method, PAPRMethod):
            raise TypeError(
                "method must be an instance of PAPRMethod."
            )

        # Intentionally accept any PAPRMethod so that other modules
        # (clipping, SLM, ...) can reuse this common result container.
        # The specific method identity is still recorded in self.method.

        if not isinstance(self.meta, dict):
            raise TypeError(
                "meta must be a dictionary."
            )

    @property
    def waveform_size(self) -> int:
        """
        Number of complex samples in the returned waveform.
        """

        return int(np.asarray(self.waveform).size)

    @property
    def n_samples_used(self) -> int:
        """
        Number of samples used for PAPR measurement.
        """

        value = self.meta.get("n_samples_used", 0)

        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @property
    def modified(self) -> bool:
        """
        Whether the PAPR algorithm modified the waveform.

        For NONE this is always False.
        """

        return bool(self.meta.get("modified", False))

    @property
    def cp_excluded(self) -> bool:
        """
        Whether CP exclusion was applied during PAPR measurement.
        """

        return bool(self.meta.get("cp_excluded", False))

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result into a JSON-friendly dictionary.
        """

        return {
            "method": self.method.value,
            "papr": self.papr.to_dict(),
            "meta": dict(self.meta),
            "waveform_size": self.waveform_size,
            "n_samples_used": self.n_samples_used,
            "modified": self.modified,
            "cp_excluded": self.cp_excluded,
        }


# ============================================================================
# Internal input extraction
# ============================================================================


def _extract_signal(
    waveform: OFDMSignal | ComplexArray | TransmitFrame,
) -> tuple[np.ndarray, np.ndarray, bool, dict[str, Any]]:
    """
    Extract full waveform and PAPR measurement samples.

    Returns
    -------
    full:
        Complete waveform.

    useful:
        Samples used for PAPR measurement.

    cp_excluded:
        Whether CP exclusion was applied.

    metadata:
        Input-related diagnostic information.
    """

    # ------------------------------------------------------------------------
    # TransmitFrame
    # ------------------------------------------------------------------------

    if isinstance(waveform, TransmitFrame):

        signal = waveform.waveform

        if not isinstance(signal, OFDMSignal):
            raise TypeError(
                "TransmitFrame.waveform must contain an OFDMSignal."
            )

        full = np.asarray(
            signal.samples,
            dtype=np.complex128,
        )

        useful = np.asarray(
            get_useful_samples(signal),
            dtype=np.complex128,
        )

        return (
            full,
            useful,
            True,
            {
                "input_type": "TransmitFrame",
                "fft_size": int(signal.fft_size),
                "cyclic_prefix_length": int(
                    signal.cyclic_prefix_length
                ),
                "oversampling": int(signal.oversampling),
            },
        )

    # ------------------------------------------------------------------------
    # OFDMSignal
    # ------------------------------------------------------------------------

    if isinstance(waveform, OFDMSignal):

        full = np.asarray(
            waveform.samples,
            dtype=np.complex128,
        )

        useful = np.asarray(
            get_useful_samples(waveform),
            dtype=np.complex128,
        )

        return (
            full,
            useful,
            True,
            {
                "input_type": "OFDMSignal",
                "fft_size": int(waveform.fft_size),
                "cyclic_prefix_length": int(
                    waveform.cyclic_prefix_length
                ),
                "oversampling": int(waveform.oversampling),
            },
        )

    # ------------------------------------------------------------------------
    # Raw complex array
    # ------------------------------------------------------------------------

    validate_complex_signal(waveform)

    full = np.asarray(
        waveform,
        dtype=np.complex128,
    )

    useful = full.ravel()

    return (
        full,
        useful,
        False,
        {
            "input_type": "ComplexArray",
            "fft_size": None,
            "cyclic_prefix_length": None,
            "oversampling": None,
        },
    )


# ============================================================================
# Validation helpers
# ============================================================================


def _validate_measurement_samples(samples: np.ndarray) -> None:
    """
    Validate the samples used for PAPR measurement.
    """

    if samples.size == 0:
        raise ValueError(
            "Cannot calculate PAPR for an empty waveform."
        )

    if not np.all(np.isfinite(samples.real)):
        raise ValueError(
            "PAPR measurement samples contain non-finite real values."
        )

    if not np.all(np.isfinite(samples.imag)):
        raise ValueError(
            "PAPR measurement samples contain non-finite imaginary values."
        )


def _validate_rng(
    rng: Optional[np.random.Generator],
) -> None:
    """
    Validate the optional RNG argument.

    NONE does not consume randomness, but accepting the common RNG interface
    makes it compatible with the rest of the PAPR pipeline.
    """

    if rng is not None and not isinstance(
        rng,
        np.random.Generator,
    ):
        raise TypeError(
            "rng must be numpy.random.Generator or None."
        )


# ============================================================================
# Core implementation
# ============================================================================


def apply_none(
    waveform: OFDMSignal | ComplexArray | TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Apply the NONE/reference PAPR method.

    The waveform is not modified.

    Parameters
    ----------
    waveform:
        Input OFDM waveform.

        Supported types:

        - ``TransmitFrame``
        - ``OFDMSignal``
        - complex NumPy array

    rng:
        Optional random-number generator.

        It is deliberately unused. It is accepted to maintain the common
        method signature shared by all PAPR algorithms.

    **kwargs:
        Additional pipeline parameters.

        NONE ignores algorithm-specific parameters. They are accepted to
        preserve compatibility with generic experiment runners.

    Returns
    -------
    PAPRProcessResult
        Unmodified waveform and measured baseline PAPR.

    Notes
    -----
    The PAPR metric is computed from useful samples only for structured OFDM
    inputs.

    For raw arrays, all supplied samples are considered useful because the
    method has no CP metadata from which to identify a cyclic prefix.
    """

    _validate_rng(rng)

    full, useful, cp_excluded, input_meta = _extract_signal(
        waveform
    )

    useful = np.asarray(
        useful,
        dtype=np.complex128,
    ).ravel()

    full = np.asarray(
        full,
        dtype=np.complex128,
    )

    _validate_measurement_samples(useful)

    # ------------------------------------------------------------------------
    # Scientific reference metric
    # ------------------------------------------------------------------------

    papr = make_papr_result(
        useful,
        cp_excluded=cp_excluded,
    )

    # ------------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------------

    meta: dict[str, Any] = {
        "method": METHOD_NAME,
        "baseline": True,
        "reference": True,
        "modified": False,
        "cp_excluded": cp_excluded,
        "n_samples_used": int(useful.size),
        "waveform_size": int(full.size),
        "input_type": input_meta["input_type"],
        "fft_size": input_meta["fft_size"],
        "cyclic_prefix_length": input_meta[
            "cyclic_prefix_length"
        ],
        "oversampling": input_meta["oversampling"],
        "rng_used": False,
        "algorithm": "identity",
    }

    # Preserve explicitly supplied diagnostic information without allowing
    # callers to overwrite scientific invariants.
    if kwargs:
        meta["ignored_kwargs"] = sorted(
            str(key)
            for key in kwargs.keys()
        )

    # ------------------------------------------------------------------------
    # Return an independent waveform copy.
    #
    # This is intentional. NONE must not modify the caller's array, but
    # returning the original object would still allow accidental mutation
    # after this function returns.
    # ------------------------------------------------------------------------

    output_waveform = np.array(
        full,
        dtype=np.complex128,
        copy=True,
    )

    return PAPRProcessResult(
        waveform=output_waveform,
        papr=papr,
        method=METHOD,
        meta=meta,
    )


# ============================================================================
# Pipeline-facing API
# ============================================================================


def process(
    transmit_frame: TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Pipeline-facing NONE processor.

    Parameters
    ----------
    transmit_frame:
        OFDM transmit frame.

    rng:
        Accepted for common pipeline compatibility.

    **kwargs:
        Additional pipeline parameters.

    Returns
    -------
    PAPRResult
        Baseline PAPR measurement.

    Important
    ---------
    The waveform remains stored in the original ``TransmitFrame``.
    This function returns only the metric because the current Stage-1
    pipeline does not require a modified waveform for the NONE method.
    """

    if not isinstance(transmit_frame, TransmitFrame):
        raise TypeError(
            "process() requires a TransmitFrame."
        )

    result = apply_none(
        transmit_frame,
        rng=rng,
        **kwargs,
    )

    return result.papr


# ============================================================================
# Convenience API
# ============================================================================


def measure(
    waveform: OFDMSignal | ComplexArray | TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """
    Measure baseline PAPR without exposing the intermediate process result.
    """

    result = apply_none(
        waveform,
        rng=rng,
        **kwargs,
    )

    return result.papr


def analyze(
    waveform: OFDMSignal | ComplexArray | TransmitFrame,
    *,
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Return the complete baseline processing result.

    This is useful for debugging, analysis notebooks, and result exporters.
    """

    return apply_none(
        waveform,
        rng=rng,
        **kwargs,
    )


# ============================================================================
# Baseline information
# ============================================================================


def method_name() -> str:
    """
    Return the canonical method name.
    """

    return METHOD_NAME


def is_baseline() -> bool:
    """
    Return True because NONE is the scientific reference.
    """

    return IS_BASELINE


def modifies_waveform() -> bool:
    """
    Return False because NONE is an identity operation.
    """

    return False


def excludes_cp() -> bool:
    """
    Return the CP-exclusion policy of the method.
    """

    return CP_EXCLUDED


def description() -> str:
    """
    Return a human-readable method description.
    """

    return (
        "Identity/reference PAPR measurement with no waveform "
        "modification. PAPR is evaluated on useful OFDM samples "
        "with cyclic-prefix samples excluded when OFDM metadata "
        "is available."
    )


def metadata() -> Mapping[str, Any]:
    """
    Return static metadata describing the NONE method.
    """

    return {
        "name": METHOD_NAME,
        "method": METHOD_NAME,
        "baseline": True,
        "reference": True,
        "implemented": True,
        "modifies_waveform": False,
        "cp_excluded": True,
        "randomness": False,
        "algorithm": "identity",
        "stage": "Stage-1",
        "description": description(),
    }


# ============================================================================
# Compatibility aliases
# ============================================================================

# Historical/simple aliases retained intentionally.
none = process

identity = process


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    # Result
    "PAPRProcessResult",

    # Constants
    "METHOD",
    "METHOD_NAME",
    "IS_BASELINE",
    "CP_EXCLUDED",

    # Core processing
    "apply_none",
    "process",

    # Convenience processing
    "measure",
    "analyze",

    # Method information
    "method_name",
    "is_baseline",
    "modifies_waveform",
    "excludes_cp",
    "description",
    "metadata",

    # Compatibility aliases
    "none",
    "identity",
]
