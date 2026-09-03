"""
PAPR Method: Selected Mapping (SLM)
===================================

Classic Selected Mapping for OFDM PAPR reduction.

Algorithm
---------
Given frequency-domain OFDM symbols X (per OFDM block):

1. Generate U candidate phase vectors B_u, u = 0 … U-1.
2. For each candidate: X_u = X ⊙ B_u  (element-wise).
3. IFFT (with project oversampling) → x_u.
4. Measure PAPR on useful (non-CP) samples.
5. Select the candidate with the lowest PAPR.
6. Return the corresponding time-domain waveform (with CP) and
   side-information (selected phase indices).

Phase sets
----------
- "bipolar"  : {+1, -1}          (default, 1 bit SI per tone or per block)
- "qpsk"     : {+1, -1, +j, -j}

Reproducibility
---------------
Phase vectors are drawn from the injected RNG stream (papr stream).
When rng is None a deterministic default seed is used.

PAPR is always evaluated on useful samples only (project contract).
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    FFTNormalization,
    OFDMGrid,
    OFDMSignal,
    PAPRMethod,
    PAPRResult,
    TransmitFrame,
    make_papr_result,
    numpy_fft_norm,
    validate_complex_signal,
    validate_positive_integer,
)
from ofdm_linksim.ofdm_modulator import ofdm_ifft, add_cyclic_prefix
from ofdm_linksim.papr import get_useful_samples
from papr_methods.none import PAPRProcessResult


METHOD = PAPRMethod.SLM
METHOD_NAME = METHOD.value
IMPLEMENTED = True
STAGE = "Phase-2"


def _phase_alphabet(name: str) -> ComplexArray:
    name = str(name).lower()
    if name in {"bipolar", "pm", "±1", "+-1"}:
        return np.array([1.0 + 0j, -1.0 + 0j], dtype=np.complex128)
    if name in {"qpsk", "4psk", "±1±j"}:
        return np.array(
            [1.0 + 0j, -1.0 + 0j, 0.0 + 1j, 0.0 - 1j],
            dtype=np.complex128,
        )
    raise ValueError(
        f"Unknown phase_set {name!r}. Expected 'bipolar' or 'qpsk'."
    )


def _draw_phase_vectors(
    n_candidates: int,
    n_tones: int,
    alphabet: ComplexArray,
    rng: np.random.Generator,
) -> ComplexArray:
    """
    Return array of shape (n_candidates, n_tones) of phase factors.
    Candidate 0 is the all-ones (identity) vector for fair comparison.
    """
    phases = np.empty((n_candidates, n_tones), dtype=np.complex128)
    phases[0, :] = 1.0 + 0j
    if n_candidates > 1:
        idx = rng.integers(0, len(alphabet), size=(n_candidates - 1, n_tones))
        phases[1:, :] = alphabet[idx]
    return phases


def _grid_from_frame(frame: TransmitFrame) -> OFDMGrid:
    return frame.ofdm_grid


def _rebuild_time(
    grid_symbols: ComplexArray,
    template: OFDMSignal,
    data_indices: np.ndarray,
    pilot_indices: np.ndarray,
    active_indices: np.ndarray,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
) -> tuple[ComplexArray, ComplexArray]:
    """
    Build full (with CP) and useful time-domain waveforms from
    frequency-domain symbols of shape (n_sym, fft_size).
    """
    grid = OFDMGrid(
        symbols=grid_symbols,
        active_indices=active_indices,
        pilot_indices=pilot_indices,
        data_indices=data_indices,
    )
    useful = ofdm_ifft(
        grid,
        oversampling=template.oversampling,
        norm=fft_norm,
    )
    if template.cp_included and template.cyclic_prefix_length > 0:
        full = add_cyclic_prefix(
            useful,
            cp_length=template.cyclic_prefix_length,
            oversampling=template.oversampling,
        )
    else:
        full = useful
    return full, useful


def apply_slm(
    waveform: OFDMSignal | ComplexArray | TransmitFrame,
    *,
    n_candidates: int = 8,
    phase_set: str = "bipolar",
    rng: Optional[np.random.Generator] = None,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Apply Selected Mapping and measure PAPR on useful samples.

    Parameters
    ----------
    n_candidates :
        Number of phase-mapped candidates (U). Typical: 4, 8, 16.
    phase_set :
        ``"bipolar"`` ({±1}) or ``"qpsk"`` ({±1, ±j}).
    rng :
        Injected random stream (papr stream). Required for reproducibility.
    """
    validate_positive_integer(n_candidates, "n_candidates")
    if n_candidates < 1:
        raise ValueError("n_candidates must be >= 1.")

    if not isinstance(waveform, TransmitFrame):
        raise TypeError(
            "SLM requires a TransmitFrame (needs frequency-domain grid). "
            "Pass the TransmitFrame produced by modulate_ofdm."
        )

    frame: TransmitFrame = waveform
    ofdm_signal = frame.waveform
    grid = frame.ofdm_grid
    n_sym = grid.n_symbols
    fft_size = grid.fft_size
    data_idx = np.asarray(grid.data_indices, dtype=np.int64)
    pilot_idx = np.asarray(grid.pilot_indices, dtype=np.int64)
    active_idx = np.asarray(grid.active_indices, dtype=np.int64)

    # Work on a copy of frequency-domain symbols
    X = np.asarray(grid.symbols, dtype=np.complex128).copy()
    if X.ndim == 1:
        X = X[np.newaxis, :]

    alphabet = _phase_alphabet(phase_set)
    if rng is None:
        rng = np.random.default_rng(0)

    # Phase vectors apply to data subcarriers; pilots stay untouched
    n_data = len(data_idx)
    phase_vecs = _draw_phase_vectors(n_candidates, n_data, alphabet, rng)

    best_papr = np.inf
    best_full: Optional[ComplexArray] = None
    best_useful: Optional[ComplexArray] = None
    best_u = 0
    best_phases: Optional[ComplexArray] = None

    for u in range(n_candidates):
        X_u = X.copy()
        # Apply phases only on data tones
        X_u[:, data_idx] = X[:, data_idx] * phase_vecs[u][np.newaxis, :]

        full_u, useful_u = _rebuild_time(
            X_u,
            ofdm_signal,
            data_idx,
            pilot_idx,
            active_idx,
            fft_norm=fft_norm,
        )
        papr_lin = float(
            np.max(np.abs(useful_u) ** 2) / np.mean(np.abs(useful_u) ** 2)
        )
        if papr_lin < best_papr:
            best_papr = papr_lin
            best_full = full_u
            best_useful = useful_u
            best_u = u
            best_phases = phase_vecs[u].copy()

    assert best_full is not None and best_useful is not None
    papr = make_papr_result(best_useful.ravel(), cp_excluded=True)

    # Side information: index of selected candidate (log2(U) bits)
    # plus optional phase snapshot for exact recovery
    meta = {
        "n_candidates": int(n_candidates),
        "phase_set": phase_set,
        "selected_candidate": int(best_u),
        "side_info_bits": int(np.ceil(np.log2(max(n_candidates, 1)))),
        "selected_phases": best_phases.tolist() if best_phases is not None else [],
        "cp_excluded": True,
        "n_samples_used": int(best_useful.size),
        "modified": best_u != 0,
        "papr_linear_selected": float(best_papr),
    }

    return PAPRProcessResult(
        waveform=best_full,
        papr=papr,
        method=PAPRMethod.SLM,
        meta=meta,
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    n_candidates: int = 8,
    phase_set: str = "bipolar",
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    """Pipeline entry: returns PAPRResult after SLM."""
    result = apply_slm(
        transmit_frame,
        n_candidates=n_candidates,
        phase_set=phase_set,
        rng=rng,
        **kwargs,
    )
    return result.papr


def method_name() -> str:
    return METHOD_NAME


def is_implemented() -> bool:
    return IMPLEMENTED


def stage() -> str:
    return STAGE


def description() -> str:
    return (
        "Selected Mapping (SLM): evaluate U phase-rotated candidates "
        "and keep the minimum-PAPR waveform."
    )


def metadata() -> dict[str, Any]:
    return {
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "parameters": {
            "n_candidates": "int >= 1 (default 8)",
            "phase_set": "'bipolar' | 'qpsk'",
        },
    }


# Alias
slm = apply_slm

__all__ = [
    "apply_slm",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "slm",
    "METHOD",
    "IMPLEMENTED",
]
