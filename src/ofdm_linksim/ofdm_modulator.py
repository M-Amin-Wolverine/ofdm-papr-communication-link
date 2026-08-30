"""
OFDM Modulator
==============

Maps modulation symbols onto an OFDM frequency grid, performs the
IFFT (with optional oversampling) and inserts the cyclic prefix.

Stage-1 responsibilities
------------------------
- Build a valid ``OFDMGrid``
- Produce a time-domain ``OFDMSignal`` (with CP)
- Assemble the canonical ``TransmitFrame``

Locked project conventions
--------------------------
1. ``cyclic_prefix_length`` is always expressed in *original-rate* samples.
   Real CP samples after oversampling = cp_length × oversampling.
2. PAPR is later evaluated only on the useful (non-CP) samples.
3. FFT normalisation follows ``FFTNormalization`` (default UNITARY → ortho).
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from ofdm_linksim.core.types import (
    BitArray,
    ComplexArray,
    IntArray,
    OFDMGrid,
    OFDMSignal,
    TransmitFrame,
    FFTNormalization,
    MappingType,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERSAMPLING,
    DEFAULT_CP_LENGTH,
    numpy_fft_norm,
    validate_bits,
    validate_complex_signal,
    validate_fft_size,
    validate_oversampling,
    validate_positive_integer,
)


# ---------------------------------------------------------------------------
# Subcarrier index helpers
# ---------------------------------------------------------------------------

def build_symmetric_data_indices(
    fft_size: int,
    n_data: int,
    *,
    exclude_dc: bool = True,
) -> IntArray:
    """
    Place data subcarriers symmetrically around DC (common research baseline).

    Negative frequencies occupy the upper half of the FFT bin array
    (NumPy convention).
    """
    validate_fft_size(fft_size)
    validate_positive_integer(n_data, "n_data")

    if n_data > fft_size - (1 if exclude_dc else 0):
        raise ValueError(
            f"n_data={n_data} exceeds available bins for fft_size={fft_size}."
        )

    # positive frequencies: 1 .. fft_size//2 - 1  (and optionally fft_size//2)
    # negative frequencies: fft_size//2 + 1 .. fft_size - 1
    half = n_data // 2
    pos = np.arange(1, half + 1, dtype=np.int64)

    if n_data % 2 == 1:
        # one extra tone on the positive side
        pos = np.arange(1, half + 2, dtype=np.int64)
        neg = np.arange(fft_size - half, fft_size, dtype=np.int64)
    else:
        neg = np.arange(fft_size - half, fft_size, dtype=np.int64)

    indices = np.concatenate([pos, neg])
    indices = np.sort(indices)
    return indices


def build_contiguous_data_indices(
    fft_size: int,
    n_data: int,
    *,
    start: int = 1,
) -> IntArray:
    """Simple contiguous block of data subcarriers (excluding DC by default)."""
    validate_fft_size(fft_size)
    validate_positive_integer(n_data, "n_data")

    if start < 0 or start + n_data > fft_size:
        raise ValueError("Contiguous data indices fall outside the FFT grid.")

    return np.arange(start, start + n_data, dtype=np.int64)


def allocate_subcarriers(
    fft_size: int,
    n_data: int,
    *,
    n_pilots: int = 0,
    mapping: MappingType = MappingType.SYMMETRIC,
    pilot_indices: Optional[Sequence[int]] = None,
) -> tuple[IntArray, IntArray, IntArray]:
    """
    Return (active_indices, pilot_indices, data_indices).

    For Stage-1 the default is zero pilots.
    """
    if n_pilots < 0:
        raise ValueError("n_pilots cannot be negative.")

    if pilot_indices is not None:
        pilots = np.asarray(pilot_indices, dtype=np.int64)
        if len(pilots) != n_pilots and n_pilots != 0:
            # trust the explicit list
            n_pilots = len(pilots)
    else:
        pilots = np.array([], dtype=np.int64)

    if mapping is MappingType.SYMMETRIC:
        data = build_symmetric_data_indices(fft_size, n_data)
    elif mapping is MappingType.CONTIGUOUS:
        data = build_contiguous_data_indices(fft_size, n_data)
    else:
        raise ValueError(f"Unsupported MappingType: {mapping}")

    if np.intersect1d(pilots, data).size > 0:
        raise ValueError("Pilot and data indices must be disjoint.")

    active = np.sort(np.concatenate([pilots, data]))
    return active, pilots, data


# ---------------------------------------------------------------------------
# Core OFDM modulation steps
# ---------------------------------------------------------------------------

def map_symbols_to_grid(
    symbols: ComplexArray,
    data_indices: IntArray,
    fft_size: int,
    *,
    pilot_indices: Optional[IntArray] = None,
    pilot_value: complex = 1.0 + 0.0j,
) -> OFDMGrid:
    """
    Place modulation symbols onto the frequency-domain grid.

    ``symbols`` length must be an integer multiple of ``len(data_indices)``.
    """
    validate_complex_signal(symbols)
    validate_fft_size(fft_size)

    symbols = np.asarray(symbols, dtype=np.complex128).ravel()
    data_indices = np.asarray(data_indices, dtype=np.int64)
    n_data = len(data_indices)

    if n_data == 0:
        raise ValueError("data_indices cannot be empty.")

    if symbols.size % n_data != 0:
        raise ValueError(
            f"Number of symbols ({symbols.size}) is not a multiple of "
            f"data subcarriers ({n_data})."
        )

    n_ofdm = symbols.size // n_data
    grid = np.zeros((n_ofdm, fft_size), dtype=np.complex128)

    # data
    grid[:, data_indices] = symbols.reshape(n_ofdm, n_data)

    # optional constant pilots (Stage-1 usually empty)
    if pilot_indices is not None and len(pilot_indices) > 0:
        pilots = np.asarray(pilot_indices, dtype=np.int64)
        grid[:, pilots] = pilot_value

    active = np.sort(
        np.concatenate(
            [
                data_indices,
                np.asarray(pilot_indices, dtype=np.int64)
                if pilot_indices is not None
                else np.array([], dtype=np.int64),
            ]
        )
    )

    return OFDMGrid(
        symbols=grid,
        active_indices=active,
        pilot_indices=np.asarray(pilot_indices, dtype=np.int64)
        if pilot_indices is not None
        else np.array([], dtype=np.int64),
        data_indices=data_indices,
    )


def ofdm_ifft(
    grid: OFDMGrid,
    *,
    oversampling: int = DEFAULT_OVERSAMPLING,
    norm: FFTNormalization = FFTNormalization.UNITARY,
) -> ComplexArray:
    """
    IFFT with zero-padding for oversampling.

    Returns useful (non-CP) time-domain samples of shape
    (n_symbols, fft_size * oversampling).
    """
    validate_oversampling(oversampling)
    n_fft = grid.fft_size
    L = oversampling
    n_os = n_fft * L

    # frequency-domain zero-padding (centred)
    freq = np.zeros((grid.n_symbols, n_os), dtype=np.complex128)

    half = n_fft // 2
    # positive frequencies incl. DC
    freq[:, : half + 1] = grid.symbols[:, : half + 1]
    # negative frequencies
    if half > 0:
        freq[:, -half:] = grid.symbols[:, -half:]

    time = np.fft.ifft(freq, axis=-1, norm=numpy_fft_norm(norm))
    return time.astype(np.complex128, copy=False)


def add_cyclic_prefix(
    useful: ComplexArray,
    cp_length: int,
    oversampling: int,
) -> ComplexArray:
    """
    Prepend the cyclic prefix.

    ``cp_length`` is in original-rate samples.
    Actual number of samples copied = cp_length * oversampling.
    """
    if cp_length < 0:
        raise ValueError("cp_length cannot be negative.")

    cp_os = cp_length * oversampling
    if cp_os == 0:
        return useful

    # useful shape: (n_symbols, useful_len)
    if useful.ndim == 1:
        useful = useful[np.newaxis, :]

    cp = useful[:, -cp_os:]
    return np.concatenate([cp, useful], axis=-1)


# ---------------------------------------------------------------------------
# Public high-level API expected by the pipeline
# ---------------------------------------------------------------------------

def modulate_ofdm(
    symbols: ComplexArray,
    *,
    source_bits: BitArray,
    coded_bits: BitArray,
    interleaved_bits: BitArray,
    fft_size: int = DEFAULT_FFT_SIZE,
    oversampling: int = DEFAULT_OVERSAMPLING,
    cyclic_prefix_length: int = DEFAULT_CP_LENGTH,
    n_data: Optional[int] = None,
    n_pilots: int = 0,
    mapping: MappingType = MappingType.SYMMETRIC,
    pilot_indices: Optional[Sequence[int]] = None,
    fft_norm: FFTNormalization = FFTNormalization.UNITARY,
    rng: Optional[np.random.Generator] = None,  # kept for signature compatibility
    **kwargs,
) -> TransmitFrame:
    """
    Complete OFDM modulation stage.

    Parameters
    ----------
    symbols :
        Flat constellation symbols produced by the modulator.
    source_bits, coded_bits, interleaved_bits :
        Bit-level fields required by ``TransmitFrame`` (Stage-1 may
        set coded = interleaved = source).
    fft_size, oversampling, cyclic_prefix_length :
        OFDM parameters (defaults match the Research Baseline).
    n_data :
        Number of data subcarriers.  If None, inferred from
        ``len(symbols)`` once the number of OFDM symbols is known,
        or defaults to a reasonable fraction of ``fft_size``.
    n_pilots / pilot_indices :
        Optional pilot configuration (Stage-1 default = none).
    fft_norm :
        FFT normalisation convention.
    rng :
        Accepted for pipeline signature compatibility; unused in
        the deterministic Stage-1 modulator.

    Returns
    -------
    TransmitFrame
    """
    validate_complex_signal(symbols)
    validate_bits(source_bits)
    validate_bits(coded_bits)
    validate_bits(interleaved_bits)
    validate_fft_size(fft_size)
    validate_oversampling(oversampling)

    symbols = np.asarray(symbols, dtype=np.complex128).ravel()

    # ------------------------------------------------------------------
    # Determine number of data subcarriers
    # ------------------------------------------------------------------
    if n_data is None:
        # Heuristic for Stage-1: use as many tones as possible while
        # keeping a small guard band (exclude DC + a few edge bins).
        # Caller can override.
        n_data = max(fft_size // 2, 1)
        # make sure symbols fit
        if symbols.size % n_data != 0:
            # fall back to the largest divisor ≤ n_data that divides symbols.size
            for candidate in range(n_data, 0, -1):
                if symbols.size % candidate == 0 and candidate <= fft_size - 1:
                    n_data = candidate
                    break
            else:
                raise ValueError(
                    f"Cannot find a suitable n_data that divides "
                    f"{symbols.size} symbols for fft_size={fft_size}."
                )

    validate_positive_integer(n_data, "n_data")

    if symbols.size % n_data != 0:
        raise ValueError(
            f"symbols.size ({symbols.size}) must be a multiple of "
            f"n_data ({n_data})."
        )

    # ------------------------------------------------------------------
    # Subcarrier allocation
    # ------------------------------------------------------------------
    active, pilots, data = allocate_subcarriers(
        fft_size,
        n_data,
        n_pilots=n_pilots,
        mapping=mapping,
        pilot_indices=pilot_indices,
    )

    # ------------------------------------------------------------------
    # Frequency grid
    # ------------------------------------------------------------------
    grid = map_symbols_to_grid(
        symbols,
        data_indices=data,
        fft_size=fft_size,
        pilot_indices=pilots,
    )

    # ------------------------------------------------------------------
    # IFFT + oversampling
    # ------------------------------------------------------------------
    useful = ofdm_ifft(grid, oversampling=oversampling, norm=fft_norm)

    # ------------------------------------------------------------------
    # Cyclic prefix
    # ------------------------------------------------------------------
    with_cp = add_cyclic_prefix(
        useful,
        cp_length=cyclic_prefix_length,
        oversampling=oversampling,
    )

    waveform = OFDMSignal(
        samples=with_cp,                 # shape (n_symbols, total_len)
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cyclic_prefix_length,
        cp_included=True,
        n_symbols=grid.n_symbols,
    )

    # ------------------------------------------------------------------
    # Assemble TransmitFrame
    # ------------------------------------------------------------------
    return TransmitFrame(
        source_bits=source_bits,
        coded_bits=coded_bits,
        interleaved_bits=interleaved_bits,
        modulation_symbols=symbols,
        ofdm_grid=grid,
        waveform=waveform,
    )


# Alias that matches the name used by the pipeline component injection
ofdm_modulator = modulate_ofdm
