"""
PAPR Method: Partial Transmit Sequence (PTS)
=============================================

Classic adjacent-partition PTS for OFDM PAPR reduction.

Algorithm
---------
1. Partition data subcarriers into V contiguous sub-blocks.
2. Pre-compute the time-domain contribution of each sub-block (IFFT).
3. Search over phase combinations b_v ∈ phase set.
4. Form candidate x = Σ b_v · x^(v).
5. Select the combination with minimum PAPR on useful samples.
6. Return the corresponding full (with CP) waveform + side information.

Search strategies
-----------------
- exhaustive : all |B|^V combinations (only practical for small V, |B|).
- random     : evaluate n_candidates random phase vectors (default).

Phase sets
----------
- "bipolar" : {+1, -1}
- "qpsk"    : {+1, -1, +j, -j}

PAPR is always measured on useful (non-CP) samples.
"""

from __future__ import annotations

from itertools import product
from typing import Any, Optional

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
    validate_positive_integer,
)
from ofdm_linksim.ofdm_modulator import ofdm_ifft, add_cyclic_prefix
from papr_methods.none import PAPRProcessResult


METHOD = PAPRMethod.PTS
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
    raise ValueError(f"Unknown phase_set {name!r}.")


def _adjacent_partitions(
    data_indices: np.ndarray,
    n_subblocks: int,
) -> list[np.ndarray]:
    """Split data indices into V contiguous groups (as equal as possible)."""
    n = len(data_indices)
    if n_subblocks > n:
        raise ValueError(
            f"n_subblocks ({n_subblocks}) cannot exceed number of data tones ({n})."
        )
    sizes = [n // n_subblocks] * n_subblocks
    for i in range(n % n_subblocks):
        sizes[i] += 1
    parts: list[np.ndarray] = []
    start = 0
    for s in sizes:
        parts.append(data_indices[start : start + s])
        start += s
    return parts


def _subblock_time_domain(
    X: ComplexArray,
    part_indices: np.ndarray,
    fft_size: int,
    oversampling: int,
    fft_norm: FFTNormalization,
) -> ComplexArray:
    """
    IFFT of a single sub-block (other tones zeroed).
    X shape: (n_sym, fft_size)
    Returns useful time samples (n_sym, fft_size * L).
    """
    n_sym = X.shape[0]
    X_v = np.zeros_like(X)
    X_v[:, part_indices] = X[:, part_indices]
    grid = OFDMGrid(
        symbols=X_v,
        active_indices=part_indices,
        pilot_indices=np.array([], dtype=np.int64),
        data_indices=part_indices,
    )
    return ofdm_ifft(grid, oversampling=oversampling, norm=fft_norm)


def apply_pts(
    waveform: TransmitFrame | OFDMSignal | ComplexArray,
    *,
    n_subblocks: int = 4,
    n_candidates: int = 64,
    phase_set: str = "bipolar",
    search: str = "random",
    rng: Optional[np.random.Generator] = None,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
    **kwargs: Any,
) -> PAPRProcessResult:
    """
    Apply Partial Transmit Sequence PAPR reduction.

    Parameters
    ----------
    n_subblocks :
        Number of adjacent frequency-domain sub-blocks (V). Typical 2–8.
    n_candidates :
        Number of phase vectors evaluated when search='random'.
        Ignored for exhaustive search (uses all |B|^V).
    phase_set :
        'bipolar' or 'qpsk'.
    search :
        'random' (default) or 'exhaustive'.
    """
    validate_positive_integer(n_subblocks, "n_subblocks")
    validate_positive_integer(n_candidates, "n_candidates")
    search = str(search).lower()
    if search not in {"random", "exhaustive"}:
        raise ValueError("search must be 'random' or 'exhaustive'.")

    if not isinstance(waveform, TransmitFrame):
        raise TypeError(
            "PTS requires a TransmitFrame (needs frequency-domain grid)."
        )

    frame: TransmitFrame = waveform
    ofdm_signal = frame.waveform
    grid = frame.ofdm_grid
    X = np.asarray(grid.symbols, dtype=np.complex128).copy()
    if X.ndim == 1:
        X = X[np.newaxis, :]

    data_idx = np.asarray(grid.data_indices, dtype=np.int64)
    pilot_idx = np.asarray(grid.pilot_indices, dtype=np.int64)
    active_idx = np.asarray(grid.active_indices, dtype=np.int64)
    fft_size = grid.fft_size
    L = ofdm_signal.oversampling

    partitions = _adjacent_partitions(data_idx, n_subblocks)
    alphabet = _phase_alphabet(phase_set)

    # Pre-compute time-domain of each sub-block (+ pilots kept in block 0)
    # Pilots are left unrotated: fold them into sub-block 0 contribution.
    sub_td: list[ComplexArray] = []
    for v, part in enumerate(partitions):
        X_part = X.copy()
        # zero everything first
        mask = np.ones(fft_size, dtype=bool)
        mask[part] = False
        if v == 0 and len(pilot_idx):
            mask[pilot_idx] = False  # keep pilots in sub-block 0
        X_part[:, mask] = 0.0
        td = ofdm_ifft(
            OFDMGrid(
                symbols=X_part,
                active_indices=np.where(~mask)[0],
                pilot_indices=pilot_idx if v == 0 else np.array([], dtype=np.int64),
                data_indices=part,
            ),
            oversampling=L,
            norm=fft_norm,
        )
        sub_td.append(td)

    if rng is None:
        rng = np.random.default_rng(0)

    # Build candidate phase vectors (first is all-ones)
    if search == "exhaustive":
        all_combos = list(product(range(len(alphabet)), repeat=n_subblocks))
        # Cap safety
        if len(all_combos) > 4096:
            raise ValueError(
                f"Exhaustive search would evaluate {len(all_combos)} candidates. "
                "Reduce n_subblocks / phase_set or use search='random'."
            )
        phase_idx_list = all_combos
    else:
        phase_idx_list = [tuple([0] * n_subblocks)]  # identity
        for _ in range(n_candidates - 1):
            phase_idx_list.append(
                tuple(rng.integers(0, len(alphabet), size=n_subblocks).tolist())
            )

    best_papr = np.inf
    best_useful: Optional[ComplexArray] = None
    best_phases_idx: tuple = phase_idx_list[0]
    best_b: Optional[ComplexArray] = None

    for combo in phase_idx_list:
        b = alphabet[list(combo)]
        # x = Σ b_v * x^(v)
        useful = np.zeros_like(sub_td[0])
        for v in range(n_subblocks):
            useful = useful + b[v] * sub_td[v]

        p_avg = float(np.mean(np.abs(useful) ** 2))
        if p_avg <= 0.0:
            continue
        papr_lin = float(np.max(np.abs(useful) ** 2) / p_avg)
        if papr_lin < best_papr:
            best_papr = papr_lin
            best_useful = useful
            best_phases_idx = combo
            best_b = b.copy()

    assert best_useful is not None and best_b is not None

    if ofdm_signal.cp_included and ofdm_signal.cyclic_prefix_length > 0:
        full = add_cyclic_prefix(
            best_useful,
            cp_length=ofdm_signal.cyclic_prefix_length,
            oversampling=L,
        )
    else:
        full = best_useful

    papr = make_papr_result(best_useful.ravel(), cp_excluded=True)

    meta = {
        "n_subblocks": int(n_subblocks),
        "n_candidates_evaluated": len(phase_idx_list),
        "phase_set": phase_set,
        "search": search,
        "selected_phases": best_b.tolist(),
        "selected_phase_indices": list(best_phases_idx),
        "side_info_bits": int(
            n_subblocks * np.ceil(np.log2(max(len(alphabet), 1)))
        ),
        "cp_excluded": True,
        "n_samples_used": int(best_useful.size),
        "modified": any(i != 0 for i in best_phases_idx),
        "papr_linear_selected": float(best_papr),
    }

    return PAPRProcessResult(
        waveform=full,
        papr=papr,
        method=PAPRMethod.PTS,
        meta=meta,
    )


def process(
    transmit_frame: TransmitFrame,
    *,
    n_subblocks: int = 4,
    n_candidates: int = 64,
    phase_set: str = "bipolar",
    search: str = "random",
    rng: Optional[np.random.Generator] = None,
    **kwargs: Any,
) -> PAPRResult:
    result = apply_pts(
        transmit_frame,
        n_subblocks=n_subblocks,
        n_candidates=n_candidates,
        phase_set=phase_set,
        search=search,
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
        "Partial Transmit Sequence (PTS): partition data tones into V "
        "sub-blocks, optimise phase factors, keep minimum-PAPR candidate."
    )


def metadata() -> dict[str, Any]:
    return {
        "method": METHOD_NAME,
        "implemented": IMPLEMENTED,
        "stage": STAGE,
        "parameters": {
            "n_subblocks": "int >= 2 (default 4)",
            "n_candidates": "int (default 64, random search)",
            "phase_set": "'bipolar' | 'qpsk'",
            "search": "'random' | 'exhaustive'",
        },
    }


pts = apply_pts

__all__ = [
    "apply_pts",
    "process",
    "method_name",
    "is_implemented",
    "stage",
    "description",
    "metadata",
    "pts",
    "METHOD",
    "IMPLEMENTED",
]
