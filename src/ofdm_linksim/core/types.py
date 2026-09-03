"""
Core data types for OFDM-PAPR-LinkSim
=====================================

This module defines the strongly-typed data contracts shared across the
entire simulation pipeline of the OFDM-PAPR-LinkSim research framework.

It is the single source of truth for all data interfaces between:

    Source
        → Coding
        → Interleaving
        → Modulation
        → OFDM Modulation
        → PAPR Analysis
        → Channel
        → Synchronization
        → Equalization
        → Demodulation
        → Decoding
        → Performance Analysis

No simulation algorithm is implemented here.
Only data contracts, enumerations, validation helpers and
lightweight utility methods are provided.

Design principles
-----------------
- Explicit and stable data contracts
- Full reproducibility support
- Strict separation of concerns
- Structurally immutable result containers (frozen dataclasses)
- Automatic validation on construction via __post_init__
- Python 3.10+ compatibility
- Native NumPy integration
- Ready for future research phases (coding, fading, PA models,
  advanced PAPR methods, complexity analysis, …)

Important conventions locked for the whole project
--------------------------------------------------
1. Cyclic-prefix length is always expressed in original-rate samples.
   Oversampling is a separate dimension.
   → Real CP samples in an oversampled waveform = cp_length × oversampling

2. PAPR is always evaluated on the useful (non-CP) samples only.

3. Shape conventions (Stage 1):

       Bits                     : (n_bits,)
       Modulation symbols       : (n_mod_symbols,)
       OFDM Grid                : (n_ofdm_symbols, fft_size)
       Useful time-domain       : (n_ofdm_symbols, fft_size × L)
       Transmitted time-domain  : (n_ofdm_symbols, (fft_size + cp) × L)

Version
-------
v1.2  – Bug fixes, stricter validation, cleaned FFT normalization,
        pure data CCDFResult, formal shape contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import (
    TypeAlias,
    Optional,
    Sequence,
    Any,
    Dict,
    Tuple,
)

from datetime import datetime, timezone
import hashlib
import json
import warnings

import numpy as np


# =============================================================================
# Fundamental Array Type Aliases
# =============================================================================

RealArray: TypeAlias = np.ndarray          # Recommended dtype: float64
ComplexArray: TypeAlias = np.ndarray       # Recommended dtype: complex128
BitArray: TypeAlias = np.ndarray           # Recommended dtype: uint8 or bool
IntArray: TypeAlias = np.ndarray           # Recommended dtype: int64


# =============================================================================
# Enumerations – Core (Stage 1)
# =============================================================================


class ModulationType(str, Enum):
    """Supported digital modulation schemes.

    Research baseline uses QPSK.
    Higher-order QAM schemes are reserved for later experiments
    that study the interaction between constellation order and PAPR.
    """

    QPSK = "QPSK"
    QAM16 = "16QAM"
    QAM64 = "64QAM"
    QAM256 = "256QAM"
    QAM1024 = "1024QAM"


class ChannelType(str, Enum):
    """Supported communication channel models.

    Phase 1 is locked to AWGN.
    Rayleigh and Rician are prepared for Phase 2.
    """

    AWGN = "AWGN"
    RAYLEIGH = "Rayleigh"
    RICIAN = "Rician"


class EqualizerType(str, Enum):
    """Supported frequency-domain equalization methods.

    For pure AWGN the equalizer is disabled.
    ZF / MMSE become relevant once frequency-selective fading is introduced.
    """

    NONE = "none"
    ZF = "ZF"
    MMSE = "MMSE"


class PAPRMethod(str, Enum):
    """PAPR processing methods.

    ``NONE`` is the locked scientific reference of the Research Baseline.
    All future algorithms are compared against this unprocessed OFDM reference.
    """

    NONE = "none"
    CLIPPING = "clipping"
    SLM = "slm"
    PTS = "pts"
    TONE_RESERVATION = "tone_reservation"
    ACE = "ace"


class CodingType(str, Enum):
    """Channel-coding configuration.

    Baseline is intentionally uncoded so that BER changes can be
    attributed solely to the PAPR-reduction algorithm (or the channel).
    """

    NONE = "none"


class InterleavingType(str, Enum):
    """Interleaving configuration.

    Disabled in the locked baseline for the same scientific reason
    as channel coding.
    """

    NONE = "none"


class FFTNormalization(str, Enum):
    """FFT / IFFT normalization convention used inside the project.

    UNITARY is the recommended setting because it preserves signal energy.
    When calling NumPy, UNITARY must be mapped to norm="ortho".
    """

    UNITARY = "unitary"      # → np.fft … norm="ortho"
    BACKWARD = "backward"    # classic 1/N on inverse
    FORWARD = "forward"      # 1/N on forward


class SNRDefinition(str, Enum):
    """How the signal-to-noise ratio is defined in the system.

    For OFDM the preferred definition is Es/N0.
    """

    EsN0 = "EsN0"
    EbN0 = "EbN0"
    SNR = "SNR"


class MappingType(str, Enum):
    """Subcarrier mapping style inside the FFT grid."""

    SYMMETRIC = "symmetric"
    CONTIGUOUS = "contiguous"
    CUSTOM = "custom"


class Units(str, Enum):
    """Physical / reporting units used throughout the framework."""

    LINEAR = "linear"
    DB = "dB"
    PERCENT = "percent"
    SAMPLES = "samples"
    HZ = "Hz"
    DB_PER_HZ = "dB/Hz"


# =============================================================================
# Enumerations – Reserved for future phases (commented)
# =============================================================================

# ----- Stage 2 / Phase 2 (Fading & Power Amplifier) -------------------------
# class FadingType(str, Enum):
#     FLAT_RAYLEIGH = "flat_rayleigh"
#     FREQUENCY_SELECTIVE_RAYLEIGH = "freq_sel_rayleigh"
#     FLAT_RICIAN = "flat_rician"
#     FREQUENCY_SELECTIVE_RICIAN = "freq_sel_rician"
#
# class PowerAmplifierModel(str, Enum):
#     NONE = "none"
#     SOFT_LIMITER = "soft_limiter"
#     RAPP = "rapp"
#     SALEH = "saleh"
#     GHORBANI = "ghorbani"
#
# class DopplerSpectrum(str, Enum):
#     CLASSICAL = "classical"      # Jakes
#     GAUSSIAN = "gaussian"
#     FLAT = "flat"

# ----- Stage 3 (Advanced metrics & complexity) ------------------------------
# class ComplexityMetric(str, Enum):
#     COMPLEX_MULTIPLIES = "complex_multiplies"
#     COMPLEX_ADDS = "complex_adds"
#     MEMORY_BYTES = "memory_bytes"
#     LATENCY_SAMPLES = "latency_samples"
#     LATENCY_SECONDS = "latency_seconds"
#
# class ThroughputMetric(str, Enum):
#     INFORMATION_BITS_PER_SYMBOL = "info_bits_per_symbol"
#     CODED_BITS_PER_SYMBOL = "coded_bits_per_symbol"
#     SPECTRAL_EFFICIENCY = "spectral_efficiency"

# ----- Stage 4 (Industrial / publication features) --------------------------
# class SerializationFormat(str, Enum):
#     JSON = "json"
#     MSGPACK = "msgpack"
#     HDF5 = "hdf5"
#     ZARR = "zarr"
#     NUMPY_NPZ = "npz_npz"


# =============================================================================
# OFDM Signal Representation
# =============================================================================


@dataclass(slots=True)
class OFDMGrid:
    """Frequency-domain representation of one or more OFDM symbols.

    Shape convention
    ----------------
    symbols : (n_ofdm_symbols, fft_size)  or  (fft_size,)

    Invariants enforced at construction
    -----------------------------------
    - pilot_indices ∩ data_indices = ∅
    - active_indices = pilot_indices ∪ data_indices
      (for the current Research Baseline; may be relaxed later
       if null/reserved carriers are introduced inside “active”)
    """

    symbols: ComplexArray
    active_indices: IntArray
    pilot_indices: IntArray
    data_indices: IntArray

    def __post_init__(self) -> None:
        if self.symbols.ndim not in (1, 2):
            raise ValueError(
                f"OFDMGrid.symbols must be 1-D or 2-D, got ndim={self.symbols.ndim}"
            )

        if not np.iscomplexobj(self.symbols):
            raise TypeError("OFDMGrid.symbols must be complex-valued.")

        if self.symbols.size == 0:
            raise ValueError("OFDMGrid.symbols cannot be empty.")

        for name, idx in (
            ("active_indices", self.active_indices),
            ("pilot_indices", self.pilot_indices),
            ("data_indices", self.data_indices),
        ):
            if not isinstance(idx, np.ndarray):
                raise TypeError(f"{name} must be a NumPy array.")

            if idx.ndim != 1:
                raise ValueError(f"{name} must be a 1-D array.")

            if not np.issubdtype(idx.dtype, np.integer):
                raise TypeError(f"{name} must contain integer indices.")

            if len(np.unique(idx)) != len(idx):
                raise ValueError(f"{name} must not contain duplicate indices.")

        if len(self.active_indices) == 0:
            raise ValueError("active_indices cannot be empty.")

        if len(self.data_indices) == 0:
            raise ValueError("data_indices cannot be empty.")

        if np.intersect1d(
            self.pilot_indices,
            self.data_indices,
        ).size > 0:
            raise ValueError(
                "pilot_indices and data_indices must be disjoint."
            )

        expected_active = np.union1d(
            self.pilot_indices,
            self.data_indices,
        )

        if not np.array_equal(
            np.sort(self.active_indices),
            np.sort(expected_active),
        ):
            raise ValueError(
                "active_indices must be exactly the union of "
                "pilot_indices and data_indices."
            )

        fft_size = self.symbols.shape[-1]

        for name, idx in (
            ("active_indices", self.active_indices),
            ("pilot_indices", self.pilot_indices),
            ("data_indices", self.data_indices),
        ):
            if np.any(idx < 0) or np.any(idx >= fft_size):
                raise ValueError(
                    f"{name} contains indices outside [0, {fft_size})."
                )

    @property
    def n_symbols(self) -> int:
        """Number of OFDM symbols stored in the grid."""
        return 1 if self.symbols.ndim == 1 else int(self.symbols.shape[0])

    @property
    def fft_size(self) -> int:
        """FFT size (number of frequency bins)."""
        return int(self.symbols.shape[-1])

    @property
    def n_active(self) -> int:
        return int(len(self.active_indices))

    @property
    def n_pilots(self) -> int:
        return int(len(self.pilot_indices))

    @property
    def n_data(self) -> int:
        return int(len(self.data_indices))

    def get_data_symbols(self) -> ComplexArray:
        """Extract only the data-bearing subcarriers."""
        if self.symbols.ndim == 1:
            return self.symbols[self.data_indices]
        return self.symbols[:, self.data_indices]

    def get_pilot_symbols(self) -> ComplexArray:
        """Extract only the pilot subcarriers."""
        if self.symbols.ndim == 1:
            return self.symbols[self.pilot_indices]
        return self.symbols[:, self.pilot_indices]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary (arrays → lists)."""
        return {
            "symbols_shape": list(self.symbols.shape),
            "active_indices": self.active_indices.tolist(),
            "pilot_indices": self.pilot_indices.tolist(),
            "data_indices": self.data_indices.tolist(),
            "n_symbols": self.n_symbols,
            "fft_size": self.fft_size,
        }


@dataclass(slots=True)
class OFDMSignal:
    """Time-domain OFDM waveform.

    Critical project-wide contracts
    -------------------------------
    1. cyclic_prefix_length is always expressed in original-rate samples.
       Real number of CP samples after oversampling =
           cyclic_prefix_length × oversampling

    2. PAPR is ALWAYS evaluated on the useful (non-CP) samples only.
       Use get_useful_samples() before calling any PAPR routine.

    Shape conventions
    -----------------
    Useful waveform   : (n_ofdm_symbols, fft_size × L)
    Transmitted (w/ CP): (n_ofdm_symbols, (fft_size + cp) × L)
    or the corresponding flat 1-D layouts.
    """

    samples: ComplexArray
    fft_size: int
    oversampling: int
    cyclic_prefix_length: int          # original-rate samples
    cp_included: bool
    n_symbols: int

    def __post_init__(self) -> None:
        # ------------------------------------------------------------------
        # Basic validation
        # ------------------------------------------------------------------
        validate_complex_signal(self.samples)
        validate_fft_size(self.fft_size)
        validate_oversampling(self.oversampling)
        validate_positive_integer(self.n_symbols, "n_symbols")

        # ------------------------------------------------------------------
        # Cyclic Prefix validation
        # ------------------------------------------------------------------
        if not isinstance(self.cyclic_prefix_length, (int, np.integer)):
            raise TypeError(
                "cyclic_prefix_length must be an integer."
            )

        if self.cyclic_prefix_length < 0:
            raise ValueError(
                "cyclic_prefix_length cannot be negative."
            )

        if self.cyclic_prefix_length > self.fft_size:
            raise ValueError(
                "cyclic_prefix_length cannot exceed fft_size."
            )

        # ------------------------------------------------------------------
        # Expected OFDM waveform lengths
        # ------------------------------------------------------------------
        expected_useful_length = (
            self.fft_size * self.oversampling
        )

        expected_total_length = (
            (self.fft_size + self.cyclic_prefix_length)
            * self.oversampling
        )

        expected_length = (
            expected_total_length
            if self.cp_included
            else expected_useful_length
        )

        expected_total_samples = (
            self.n_symbols * expected_length
        )

        # ------------------------------------------------------------------
        # Waveform shape validation
        #
        # Supported representations:
        #
        #   1-D:
        #       [total_samples]
        #
        #   2-D:
        #       [n_symbols, samples_per_symbol]
        # ------------------------------------------------------------------
        if self.samples.ndim == 1:

            if self.samples.size != expected_total_samples:
                raise ValueError(
                    "OFDMSignal.samples has an invalid length. "
                    f"Expected {expected_total_samples} samples "
                    f"for {self.n_symbols} OFDM symbols "
                    f"(expected {expected_length} samples/symbol), "
                    f"got {self.samples.size}. "
                    f"fft_size={self.fft_size}, "
                    f"oversampling={self.oversampling}, "
                    f"cyclic_prefix_length={self.cyclic_prefix_length}, "
                    f"cp_included={self.cp_included}."
                )

        elif self.samples.ndim == 2:

            expected_shape = (
                self.n_symbols,
                expected_length,
            )

            if self.samples.shape != expected_shape:
                raise ValueError(
                    "OFDMSignal.samples has an invalid shape. "
                    f"Expected {expected_shape}, "
                    f"got {self.samples.shape}. "
                    f"fft_size={self.fft_size}, "
                    f"oversampling={self.oversampling}, "
                    f"cyclic_prefix_length={self.cyclic_prefix_length}, "
                    f"cp_included={self.cp_included}."
                )

        else:

            raise ValueError(
                "OFDMSignal.samples must be either 1-D or 2-D."
            )

    @property
    def useful_length(self) -> int:
        """Length of one OFDM symbol without CP (oversampled)."""
        return self.fft_size * self.oversampling

    @property
    def cp_length_oversampled(self) -> int:
        """Actual number of CP samples after oversampling."""
        return self.cyclic_prefix_length * self.oversampling

    @property
    def total_length_per_symbol(self) -> int:
        """Length of one OFDM symbol including CP (oversampled)."""
        return self.useful_length + self.cp_length_oversampled

    @property
    def total_samples(self) -> int:
        """Total number of complex samples stored."""
        return int(self.samples.size)

    def get_useful_samples(self) -> ComplexArray:
        """
        Return only the useful (non-CP) portion of the waveform.

        This is the exact signal that must be used for PAPR calculation
        according to the locked Research Baseline.
        """
        if not self.cp_included:
            return self.samples

        useful = []
        sp_symbol = self.total_length_per_symbol
        useful_len = self.useful_length
        cp_len_os = self.cp_length_oversampled

        flat = self.samples.ravel()
        for i in range(self.n_symbols):
            start = i * sp_symbol + cp_len_os
            end = start + useful_len
            useful.append(flat[start:end])
        return np.concatenate(useful)

    def get_symbol(self, idx: int) -> ComplexArray:
        """Extract a single OFDM symbol (including CP if present)."""
        if idx < 0 or idx >= self.n_symbols:
            raise IndexError(
                f"Symbol index {idx} out of range [0, {self.n_symbols})."
            )
        sp = (
            self.total_length_per_symbol
            if self.cp_included
            else self.useful_length
        )
        start = idx * sp
        return self.samples.ravel()[start : start + sp]

    def power(self) -> float:
        """Average power of the stored samples."""
        return float(np.mean(np.abs(self.samples) ** 2))

    def peak_power(self) -> float:
        """Peak instantaneous power of the stored samples."""
        return float(np.max(np.abs(self.samples) ** 2))

    def to_dict(self) -> Dict[str, Any]:
        """Lightweight serialization (samples omitted for size reasons)."""
        return {
            "fft_size": self.fft_size,
            "oversampling": self.oversampling,
            "cyclic_prefix_length": self.cyclic_prefix_length,
            "cp_length_oversampled": self.cp_length_oversampled,
            "cp_included": self.cp_included,
            "n_symbols": self.n_symbols,
            "total_samples": self.total_samples,
            "useful_length": self.useful_length,
            "average_power": self.power(),
            "peak_power": self.peak_power(),
        }


# =============================================================================
# Transmission / Reception Frames
# =============================================================================


@dataclass(slots=True)
class TransmitFrame:
    """Complete transmitter-side data package.

    Preserves the full relationship:

        source bits
            → coded bits
            → interleaved bits
            → modulation symbols
            → frequency-domain grid
            → time-domain waveform

    Even when coding = none and interleaving = none the fields are kept
    so that later addition of LDPC / Polar / Turbo / interleavers
    does not break the architecture.
    """

    source_bits: BitArray
    coded_bits: BitArray
    interleaved_bits: BitArray
    modulation_symbols: ComplexArray
    ofdm_grid: OFDMGrid
    waveform: OFDMSignal

    def __post_init__(self) -> None:
        validate_bits(self.source_bits)
        validate_bits(self.coded_bits)
        validate_bits(self.interleaved_bits)

        if not np.iscomplexobj(self.modulation_symbols):
            raise TypeError(
                "modulation_symbols must be complex-valued."
            )

        if self.modulation_symbols.size == 0:
            raise ValueError(
                "modulation_symbols cannot be empty."
            )

        expected_symbols = (
            self.ofdm_grid.n_symbols *
            self.ofdm_grid.n_data
        )

        if self.modulation_symbols.size != expected_symbols:
            raise ValueError(
                "Number of modulation symbols does not match "
                "the OFDM grid data capacity: "
                f"expected {expected_symbols}, "
                f"got {self.modulation_symbols.size}."
            )

    @property
    def n_source_bits(self) -> int:
        return int(self.source_bits.size)

    @property
    def n_coded_bits(self) -> int:
        return int(self.coded_bits.size)

    @property
    def code_rate(self) -> float:
        """Effective code rate (1.0 for the uncoded baseline)."""
        if self.n_coded_bits == 0:
            return 1.0
        return self.n_source_bits / self.n_coded_bits

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_source_bits": self.n_source_bits,
            "n_coded_bits": self.n_coded_bits,
            "code_rate": self.code_rate,
            "n_modulation_symbols": int(self.modulation_symbols.size),
            "ofdm_grid": self.ofdm_grid.to_dict(),
            "waveform": self.waveform.to_dict(),
        }


@dataclass(slots=True)
class ReceiveFrame:
    """Complete receiver-side processing results."""

    received_waveform: OFDMSignal
    ofdm_grid: OFDMGrid
    equalized_symbols: ComplexArray
    demodulated_bits: BitArray
    decoded_bits: BitArray

    def __post_init__(self) -> None:
        validate_bits(self.demodulated_bits)
        validate_bits(self.decoded_bits)
        if not np.iscomplexobj(self.equalized_symbols):
            raise TypeError("equalized_symbols must be complex-valued.")

    @property
    def n_demodulated_bits(self) -> int:
        return int(self.demodulated_bits.size)

    @property
    def n_decoded_bits(self) -> int:
        return int(self.decoded_bits.size)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_demodulated_bits": self.n_demodulated_bits,
            "n_decoded_bits": self.n_decoded_bits,
            "ofdm_grid": self.ofdm_grid.to_dict(),
            "received_waveform": self.received_waveform.to_dict(),
        }


# =============================================================================
# Channel Output
# =============================================================================


@dataclass(slots=True)
class ChannelOutput:
    """Output of any channel model (AWGN, Rayleigh, Rician, …)."""

    signal: ComplexArray
    snr_db: float
    channel_type: ChannelType
    noise_power: float
    channel_gain: Optional[ComplexArray] = None

    def __post_init__(self) -> None:
        validate_complex_signal(self.signal)

        if not isinstance(self.channel_type, ChannelType):
            raise TypeError(
                "channel_type must be an instance of ChannelType."
            )

        validate_non_negative(
            self.noise_power,
            "noise_power",
        )

        validate_snr_db(self.snr_db)

        if self.channel_gain is not None:
            validate_complex_signal(self.channel_gain)

    @property
    def signal_power(self) -> float:
        return float(np.mean(np.abs(self.signal) ** 2))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snr_db": self.snr_db,
            "channel_type": self.channel_type.value,
            "noise_power": self.noise_power,
            "signal_power": self.signal_power,
            "has_channel_gain": self.channel_gain is not None,
        }


# =============================================================================
# PAPR Metrics (Structurally immutable)
# =============================================================================


@dataclass(frozen=True, slots=True)
class PAPRResult:
    """PAPR measurement for a single OFDM block (or a concatenated waveform).

    Definition used throughout the project:

        PAPR_linear = max_n |x[n]|²  /  mean_n |x[n]|²
        PAPR_dB      = 10 · log10(PAPR_linear)

    The cyclic prefix is ALWAYS excluded from the calculation.
    """

    papr_linear: float
    papr_db: float
    peak_power: float
    average_power: float
    peak_index: int
    cp_excluded: bool = True
    n_samples_used: int = 0

    def __post_init__(self) -> None:
        # -----------------------------------------------------------------
        # PAPR linear
        # -----------------------------------------------------------------
        if not np.isfinite(self.papr_linear):
            raise ValueError(
                "papr_linear must be finite."
            )

        if self.papr_linear < 1.0:
            raise ValueError(
                "papr_linear must be >= 1."
            )

        # -----------------------------------------------------------------
        # PAPR dB consistency
        # -----------------------------------------------------------------
        if not np.isfinite(self.papr_db):
            raise ValueError(
                "papr_db must be finite."
            )

        expected_db = 10.0 * np.log10(self.papr_linear)

        if not np.isclose(
            self.papr_db,
            expected_db,
            rtol=1e-6,
            atol=1e-9,
        ):
            raise ValueError(
                "papr_db is inconsistent with papr_linear."
            )

        # -----------------------------------------------------------------
        # Power values
        # -----------------------------------------------------------------
        if not np.isfinite(self.peak_power):
            raise ValueError(
                "peak_power must be finite."
            )

        if not np.isfinite(self.average_power):
            raise ValueError(
                "average_power must be finite."
            )

        if self.peak_power <= 0.0:
            raise ValueError(
                "peak_power must be strictly positive."
            )

        if self.average_power <= 0.0:
            raise ValueError(
                "average_power must be strictly positive."
            )

        if self.peak_power < self.average_power:
            raise ValueError(
                "peak_power cannot be smaller than average_power."
            )

        # -----------------------------------------------------------------
        # Sample metadata
        # -----------------------------------------------------------------
        if not isinstance(
            self.n_samples_used,
            (int, np.integer),
        ):
            raise TypeError(
                "n_samples_used must be an integer."
            )

        if self.n_samples_used <= 0:
            raise ValueError(
                "n_samples_used must be positive."
            )

        if not isinstance(
            self.peak_index,
            (int, np.integer),
        ):
            raise TypeError(
                "peak_index must be an integer."
            )

        if self.peak_index < 0:
            raise ValueError(
                "peak_index cannot be negative."
            )

        if self.peak_index >= self.n_samples_used:
            raise ValueError(
                "peak_index must be smaller than n_samples_used."
            )

@dataclass(frozen=True, slots=True)
class CCDFResult:
    """Empirical Complementary Cumulative Distribution Function of PAPR.

        CCDF(γ) = Pr(PAPR > γ)

    This class is intentionally a pure data container.
    Any interpolation / lookup logic lives in analysis utilities,
    not inside the data contract.
    """

    thresholds_db: RealArray
    probabilities: RealArray
    n_blocks: int
    method: str = "empirical"

    def __post_init__(self) -> None:
        thresholds = np.asarray(self.thresholds_db)
        probabilities = np.asarray(self.probabilities)

        if thresholds.ndim != 1:
            raise ValueError(
                "thresholds_db must be a 1-D array."
            )

        if probabilities.ndim != 1:
            raise ValueError(
                "probabilities must be a 1-D array."
            )

        if len(thresholds) != len(probabilities):
            raise ValueError(
                "thresholds_db and probabilities must have "
                "identical length."
            )

        if len(thresholds) == 0:
            raise ValueError(
                "CCDF cannot be empty."
            )

        if not np.all(np.isfinite(thresholds)):
            raise ValueError(
                "thresholds_db must contain only finite values."
            )

        if not np.all(np.isfinite(probabilities)):
            raise ValueError(
                "probabilities must contain only finite values."
            )

        if np.any(probabilities < 0.0) or np.any(probabilities > 1.0):
            raise ValueError(
                "All probabilities must lie in [0, 1]."
            )

        if np.any(np.diff(thresholds) < 0):
            raise ValueError(
                "thresholds_db must be monotonically increasing."
            )

        if np.any(np.diff(probabilities) > 0):
            raise ValueError(
                "CCDF probabilities must be monotonically decreasing."
            )

        if self.n_blocks <= 0:
            raise ValueError(
                "n_blocks must be a positive integer."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thresholds_db": self.thresholds_db.tolist(),
            "probabilities": self.probabilities.tolist(),
            "n_blocks": self.n_blocks,
            "method": self.method,
        }


@dataclass(frozen=True, slots=True)
class PAPRStatistics:
    """Aggregate statistical summary of many PAPR measurements.

    Useful for quick reporting without storing the full CCDF curve.
    The four classic CCDF operating points are stored explicitly.
    """

    mean_papr_db: float
    median_papr_db: float
    std_papr_db: float
    min_papr_db: float
    max_papr_db: float
    n_blocks: int
    papr_at_1e1: float          # PAPR @ CCDF = 10⁻¹
    papr_at_1e2: float          # PAPR @ CCDF = 10⁻²
    papr_at_1e3: float          # PAPR @ CCDF = 10⁻³
    papr_at_1e4: float          # PAPR @ CCDF = 10⁻⁴

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_papr_list(
        papr_db_values: Sequence[float],
        ccdf: Optional[CCDFResult] = None,
    ) -> "PAPRStatistics":
        """Construct statistics from a list of per-block PAPR values (dB)."""
        arr = np.asarray(papr_db_values, dtype=float)
        if arr.size == 0:
            raise ValueError("Cannot compute statistics on an empty PAPR list.")

        def _lookup(prob: float) -> float:
            """Simple nearest-neighbour lookup (no interpolation)."""
            if ccdf is None:
                return float("nan")
            # probabilities are expected to be monotonically decreasing
            idx = int(np.argmin(np.abs(ccdf.probabilities - prob)))
            return float(ccdf.thresholds_db[idx])

        return PAPRStatistics(
            mean_papr_db=float(np.mean(arr)),
            median_papr_db=float(np.median(arr)),
            std_papr_db=float(np.std(arr)),
            min_papr_db=float(np.min(arr)),
            max_papr_db=float(np.max(arr)),
            n_blocks=int(arr.size),
            papr_at_1e1=_lookup(1e-1),
            papr_at_1e2=_lookup(1e-2),
            papr_at_1e3=_lookup(1e-3),
            papr_at_1e4=_lookup(1e-4),
        )


# =============================================================================
# Link-Level Metrics
# =============================================================================


@dataclass(frozen=True, slots=True)
class BERResult:
    """Bit Error Rate measurement."""

    bit_errors: int
    total_bits: int
    ber: float
    snr_db: Optional[float] = None

    def __post_init__(self) -> None:
        if self.bit_errors < 0:
            raise ValueError(
                "bit_errors cannot be negative."
            )

        if self.total_bits <= 0:
            raise ValueError(
                "total_bits must be positive."
            )

        if self.bit_errors > self.total_bits:
            raise ValueError(
                "bit_errors cannot exceed total_bits."
            )

        expected_ber = self.bit_errors / self.total_bits

        if not np.isclose(
            self.ber,
            expected_ber,
            rtol=1e-6,
            atol=1e-12,
        ):
            raise ValueError(
                "BER is inconsistent with bit_errors / total_bits."
            )

        if self.snr_db is not None:
            validate_snr_db(self.snr_db)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bit_errors": self.bit_errors,
            "total_bits": self.total_bits,
            "ber": self.ber,
            "snr_db": self.snr_db,
        }


@dataclass(frozen=True, slots=True)
class EVMResult:
    """Error Vector Magnitude (both RMS and Peak).

    RMS EVM characterises average constellation degradation.
    Peak EVM highlights the worst-case symbol error.
    """

    rms_evm: float                 # linear scale
    rms_evm_percent: float
    peak_evm: float                # linear scale
    peak_evm_percent: float

    def __post_init__(self) -> None:
        if self.rms_evm < 0.0:
            raise ValueError(
                "rms_evm cannot be negative."
            )

        if self.peak_evm < 0.0:
            raise ValueError(
                "peak_evm cannot be negative."
            )

        if self.peak_evm < self.rms_evm:
            raise ValueError(
                "peak_evm cannot be smaller than rms_evm."
            )

        if not np.isclose(
            self.rms_evm_percent,
            self.rms_evm * 100.0,
            rtol=1e-6,
            atol=1e-9,
        ):
            raise ValueError(
                "rms_evm_percent is inconsistent with rms_evm."
            )

        if not np.isclose(
            self.peak_evm_percent,
            self.peak_evm * 100.0,
            rtol=1e-6,
            atol=1e-9,
        ):
            raise ValueError(
                "peak_evm_percent is inconsistent with peak_evm."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rms_evm": self.rms_evm,
            "rms_evm_percent": self.rms_evm_percent,
            "peak_evm": self.peak_evm,
            "peak_evm_percent": self.peak_evm_percent,
        }


@dataclass(frozen=True, slots=True)
class PSDResult:
    """Power Spectral Density estimate (Welch or periodogram)."""

    frequencies: RealArray
    psd_db: RealArray
    method: str = "welch"
    nperseg: int = 1024
    noverlap: int = 512
    window: str = "hann"

    def __post_init__(self) -> None:
        if self.frequencies.ndim != 1:
            raise ValueError(
                "frequencies must be a 1-D array."
            )

        if self.psd_db.ndim != 1:
            raise ValueError(
                "psd_db must be a 1-D array."
            )

        if len(self.frequencies) != len(self.psd_db):
            raise ValueError(
                "frequencies and psd_db must have the same length."
            )

        if len(self.frequencies) == 0:
            raise ValueError(
                "PSD result cannot be empty."
            )

        if not np.all(np.isfinite(self.frequencies)):
            raise ValueError(
                "frequencies must contain finite values."
            )

        if not np.all(np.isfinite(self.psd_db)):
            raise ValueError(
                "psd_db must contain finite values."
            )

        validate_positive_integer(
            self.nperseg,
            "nperseg",
        )

        if self.noverlap < 0:
            raise ValueError(
                "noverlap cannot be negative."
            )

        if self.noverlap >= self.nperseg:
            raise ValueError(
                "noverlap must be smaller than nperseg."
            )
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frequencies": self.frequencies.tolist(),
            "psd_db": self.psd_db.tolist(),
            "method": self.method,
            "nperseg": self.nperseg,
            "noverlap": self.noverlap,
            "window": self.window,
        }


@dataclass(frozen=True, slots=True)
class ConstellationSnapshot:
    """Snapshot of received (or equalized) constellation points
    together with the ideal reference constellation.

    ``n_points`` is the total number of complex samples stored in
    ``symbols`` (i.e. symbols.size).  It is derived automatically.
    """

    symbols: ComplexArray
    reference_constellation: ComplexArray
    snr_db: Optional[float] = None

    def __post_init__(self) -> None:
        if not np.iscomplexobj(self.symbols):
            raise TypeError("symbols must be complex-valued.")
        if not np.iscomplexobj(self.reference_constellation):
            raise TypeError("reference_constellation must be complex-valued.")

    @property
    def n_points(self) -> int:
        """Total number of constellation points stored."""
        return int(self.symbols.size)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_points": self.n_points,
            "snr_db": self.snr_db,
            "reference_points": self.reference_constellation.tolist(),
        }


# =============================================================================
# Configuration Snapshot (Stage-1 essential)
# =============================================================================


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    """
    Structurally immutable snapshot of the exact configuration that
    produced a given experiment result.

    Storing this object inside SimulationMetadata guarantees that
    every result can be reproduced years later without ambiguity.

    Note: the ``extra`` dictionary is still a mutable object.
    Callers must treat it as read-only after construction.
    """

    scenario_name: str
    scenario_version: str
    fft_size: int
    active_subcarriers: int
    pilot_subcarriers: int
    data_subcarriers: int
    cyclic_prefix_length: int
    oversampling_factor: int
    modulation: ModulationType
    channel: ChannelType
    snr_definition: SNRDefinition
    papr_method: PAPRMethod
    coding: CodingType
    interleaving: InterleavingType
    random_seed: int
    ofdm_blocks: int
    fft_normalization: FFTNormalization = FFTNormalization.UNITARY
    mapping_type: MappingType = MappingType.SYMMETRIC
    extra: Dict[str, Any] = field(default_factory=dict)
    def __post_init__(self) -> None:
        validate_fft_size(self.fft_size)
        validate_oversampling(self.oversampling_factor)

        validate_positive_integer(
            self.active_subcarriers,
            "active_subcarriers",
        )

        validate_positive_integer(
            self.data_subcarriers,
            "data_subcarriers",
        )

        if self.pilot_subcarriers < 0:
            raise ValueError(
                "pilot_subcarriers cannot be negative."
            )

        if self.active_subcarriers != (
            self.pilot_subcarriers +
            self.data_subcarriers
        ):
            raise ValueError(
                "active_subcarriers must equal "
                "pilot_subcarriers + data_subcarriers."
            )

        if self.active_subcarriers > self.fft_size:
            raise ValueError(
                "active_subcarriers cannot exceed fft_size."
            )

        validate_positive_integer(
            self.cyclic_prefix_length + 1,
            "cyclic_prefix_length + 1",
        )

        if self.cyclic_prefix_length > self.fft_size:
            raise ValueError(
                "cyclic_prefix_length cannot exceed fft_size."
            )

        validate_positive_integer(
            self.random_seed,
            "random_seed",
        )

        validate_positive_integer(
            self.ofdm_blocks,
            "ofdm_blocks",
        )
    def fingerprint(self) -> str:
        """Return a short stable hash of the configuration."""
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, Enum):
                d[k] = v.value
        return d


# =============================================================================
# Simulation Metadata & Aggregated Experiment Result
# =============================================================================


@dataclass(frozen=True, slots=True)
class SimulationMetadata:
    """Everything required for full reproducibility and experiment tracking."""

    seed: int
    scenario_name: str
    scenario_version: str
    n_ofdm_symbols: int
    modulation: ModulationType
    channel: ChannelType
    papr_method: PAPRMethod
    fft_size: int = 256
    oversampling: int = 4
    snr_definition: SNRDefinition = SNRDefinition.EsN0
    config_snapshot: Optional[ConfigSnapshot] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    run_id: str = field(
        default_factory=lambda: hashlib.sha1(
            str(datetime.now(timezone.utc).timestamp()).encode()
        ).hexdigest()[:12]
    )
    notes: str = ""
    def __post_init__(self) -> None:
        validate_positive_integer(
            self.seed,
            "seed",
        )

        validate_positive_integer(
            self.n_ofdm_symbols,
            "n_ofdm_symbols",
        )

        validate_fft_size(self.fft_size)
        validate_oversampling(self.oversampling)
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "seed": self.seed,
            "scenario_name": self.scenario_name,
            "scenario_version": self.scenario_version,
            "n_ofdm_symbols": self.n_ofdm_symbols,
            "modulation": self.modulation.value,
            "channel": self.channel.value,
            "papr_method": self.papr_method.value,
            "fft_size": self.fft_size,
            "oversampling": self.oversampling,
            "snr_definition": self.snr_definition.value,
            "created_at": self.created_at,
            "run_id": self.run_id,
            "notes": self.notes,
        }
        if self.config_snapshot is not None:
            d["config_snapshot"] = self.config_snapshot.to_dict()
            d["config_fingerprint"] = self.config_snapshot.fingerprint()
        return d


@dataclass(slots=True)
class ExperimentResult:
    """
    Top-level container for any experiment
    (transmitter-only PAPR study or full-link BER/EVM study).
    """

    metadata: SimulationMetadata

    # Transmitter-side metrics
    papr: Optional[PAPRResult] = None
    ccdf: Optional[CCDFResult] = None
    papr_statistics: Optional[PAPRStatistics] = None

    # Link-level metrics
    ber: Optional[BERResult] = None
    evm: Optional[EVMResult] = None
    psd: Optional[PSDResult] = None
    constellation: Optional[ConstellationSnapshot] = None

    # Optional free-form diagnostic information
    notes: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> Dict[str, Any]:
        """Return a compact human-readable summary of the experiment."""
        s: Dict[str, Any] = {
            "run_id": self.metadata.run_id,
            "scenario": (
                f"{self.metadata.scenario_name} "
                f"v{self.metadata.scenario_version}"
            ),
            "modulation": self.metadata.modulation.value,
            "channel": self.metadata.channel.value,
            "papr_method": self.metadata.papr_method.value,
            "n_ofdm_symbols": self.metadata.n_ofdm_symbols,
            "seed": self.metadata.seed,
        }
        if self.papr is not None:
            s["papr_db"] = self.papr.papr_db
        if self.papr_statistics is not None:
            s["papr_mean_db"] = self.papr_statistics.mean_papr_db
            s["papr_at_1e3"] = self.papr_statistics.papr_at_1e3
            s["papr_at_1e4"] = self.papr_statistics.papr_at_1e4
        if self.ber is not None:
            s["ber"] = self.ber.ber
            s["snr_db"] = self.ber.snr_db
        if self.evm is not None:
            s["rms_evm_percent"] = self.evm.rms_evm_percent
        return s

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "metadata": self.metadata.to_dict(),
            "notes": self.notes,
            "extra": self.extra,
        }
        if self.papr is not None:
            d["papr"] = self.papr.to_dict()
        if self.ccdf is not None:
            d["ccdf"] = self.ccdf.to_dict()
        if self.papr_statistics is not None:
            d["papr_statistics"] = self.papr_statistics.to_dict()
        if self.ber is not None:
            d["ber"] = self.ber.to_dict()
        if self.evm is not None:
            d["evm"] = self.evm.to_dict()
        if self.psd is not None:
            d["psd"] = self.psd.to_dict()
        if self.constellation is not None:
            d["constellation"] = self.constellation.to_dict()
        return d


# =============================================================================
# Validation Helpers
# =============================================================================


def validate_bits(bits: BitArray) -> None:
    """Ensure the array is non-empty and contains only binary values {0, 1}."""
    if not isinstance(bits, np.ndarray):
        raise TypeError("bits must be a NumPy ndarray.")

    if bits.ndim != 1:
        raise ValueError(
            f"bits must be 1-D, got ndim={bits.ndim}."
        )

    if bits.size == 0:
        raise ValueError(
            "Bit array must not be empty."
        )

    if not np.all((bits == 0) | (bits == 1)):
        raise ValueError(
            "Bit array must contain only the values 0 and 1."
        )


def validate_complex_signal(
    signal: ComplexArray,
) -> None:
    """Ensure the signal is a non-empty complex NumPy array."""

    if not isinstance(signal, np.ndarray):
        raise TypeError(
            "signal must be a NumPy ndarray."
        )

    if signal.size == 0:
        raise ValueError(
            "Signal array must not be empty."
        )

    if not np.iscomplexobj(signal):
        raise TypeError(
            "Signal must be complex-valued."
        )

    if not np.all(np.isfinite(signal)):
        raise ValueError(
            "Signal must contain only finite values."
        )


def validate_probability(
    value: float,
    name: str = "probability",
) -> None:
    if not np.isfinite(value):
        raise ValueError(
            f"{name} must be finite, got {value}."
        )

    if not 0.0 <= value <= 1.0:
        raise ValueError(
            f"{name} must lie in the interval [0, 1], "
            f"got {value}."
        )

def validate_positive_integer(value: int, name: str) -> None:
    """Ensure the argument is a strictly positive integer."""
    if not isinstance(value, (int, np.integer)) or value <= 0:
        raise ValueError(f"{name} must be a strictly positive integer, got {value}.")


def validate_non_negative(
    value: float,
    name: str,
) -> None:
    if not np.isfinite(value):
        raise ValueError(
            f"{name} must be finite, got {value}."
        )

    if value < 0.0:
        raise ValueError(
            f"{name} cannot be negative, got {value}."
        )

def validate_snr_db(snr_db: float) -> None:
    """Basic sanity check for an SNR value expressed in decibels."""
    if not np.isfinite(snr_db):
        raise ValueError(f"SNR must be a finite number, got {snr_db}.")
    if snr_db < -50.0 or snr_db > 100.0:
        raise ValueError(
            f"SNR value {snr_db} dB is outside the plausible range [-50, 100] dB."
        )


def validate_fft_size(fft_size: int) -> None:
    """FFT size must be a positive power of two for efficient implementation."""
    validate_positive_integer(fft_size, "fft_size")
    if fft_size & (fft_size - 1) != 0:
        raise ValueError(f"fft_size should be a power of two, got {fft_size}.")


def validate_oversampling(L: int) -> None:
    """Oversampling factor must be a positive integer (baseline = 4)."""
    validate_positive_integer(L, "oversampling_factor")
    if L > 16:
        warnings.warn(
            f"Oversampling factor L={L} is unusually high; "
            "L=4 is sufficient for accurate PAPR estimation.",
            UserWarning,
            stacklevel=2,
        )


# =============================================================================
# Utility Functions (Stage-1 helpers)
# =============================================================================


def db_to_linear(db: float) -> float:
    """Convert a value from decibels to linear scale."""
    return float(10.0 ** (float(db) / 10.0))


def linear_to_db(linear: float) -> float:
    """Convert a linear power ratio to decibels."""
    linear = float(linear)
    if linear <= 0.0:
        raise ValueError("Cannot convert non-positive value to dB.")
    return float(10.0 * np.log10(linear))



def safe_mean_power(x: ComplexArray) -> float:
    """Compute average power with protection against empty arrays."""
    if x.size == 0:
        raise ValueError("Cannot compute power of an empty array.")
    return float(np.mean(np.abs(x) ** 2))


def safe_peak_power(x: ComplexArray) -> float:
    """Compute peak instantaneous power."""
    if x.size == 0:
        raise ValueError("Cannot compute peak power of an empty array.")
    return float(np.max(np.abs(x) ** 2))


def compute_papr_linear(x: ComplexArray) -> Tuple[float, float, float, int]:
    """
    Compute PAPR in linear scale together with peak power,
    average power and the index of the peak sample.

    Returns
    -------
    papr_linear, peak_power, average_power, peak_index
    """
    power = np.abs(x) ** 2
    peak_power = float(np.max(power))
    average_power = float(np.mean(power))
    if average_power == 0.0:
        raise ValueError("Average power is zero – cannot compute PAPR.")
    peak_index = int(np.argmax(power))
    papr_linear = peak_power / average_power
    return papr_linear, peak_power, average_power, peak_index


def make_papr_result(
    x: ComplexArray,
    cp_excluded: bool = True,
) -> PAPRResult:
    """Convenience factory that builds a PAPRResult from a complex waveform.

    The caller is responsible for supplying the useful (non-CP) samples.
    """
    papr_lin, peak_p, avg_p, peak_idx = compute_papr_linear(x)
    return PAPRResult(
        papr_linear=float(papr_lin),
        papr_db=float(linear_to_db(papr_lin)),
        peak_power=float(peak_p),
        average_power=float(avg_p),
        peak_index=int(peak_idx),
        cp_excluded=cp_excluded,
        n_samples_used=int(x.size),
    )


def bits_to_int(bits: BitArray) -> int:
    """Convert an MSB-first bit array to an integer.

    This implementation is deliberately simple and free of
    packbits edge-cases.
    """
    validate_bits(bits)
    value = 0
    for bit in bits.astype(np.uint8):
        value = (value << 1) | int(bit)
    return value


def int_to_bits(value: int, n_bits: int) -> BitArray:
    if not isinstance(n_bits, (int, np.integer)):
        raise TypeError(
            "n_bits must be an integer."
        )

    if n_bits <= 0:
        raise ValueError(
            "n_bits must be positive."
        )
    """Convert an integer to a fixed-width bit array (MSB first)."""
    if value < 0:
        raise ValueError("Only non-negative integers are supported.")
    if value >= (1 << n_bits):
        raise ValueError(f"Value {value} does not fit into {n_bits} bits.")
    binary = format(value, f"0{n_bits}b")
    return np.array([int(b) for b in binary], dtype=np.uint8)


def numpy_fft_norm(norm: FFTNormalization) -> str:
    """Map project-level FFTNormalization to the string expected by np.fft."""
    if norm is FFTNormalization.UNITARY:
        return "ortho"
    return norm.value


# =============================================================================
# Reserved stubs for future phases (Stage 2 / 3 / 4)
# =============================================================================

# ----- Stage 2 : Fading & Power Amplifier ------------------------------------
#
# @dataclass(slots=True)
# class FadingRealization:
#     taps: ComplexArray
#     delays_samples: IntArray
#     power_delay_profile: RealArray
#     doppler_hz: float
#     spectrum: "DopplerSpectrum"
#
# @dataclass(slots=True)
# class PAResult:
#     input_signal: ComplexArray
#     output_signal: ComplexArray
#     input_backoff_db: float
#     output_backoff_db: float
#     model: "PowerAmplifierModel"
#     am_am: Optional[RealArray] = None
#     am_pm: Optional[RealArray] = None

# ----- Stage 3 : Complexity & Throughput ------------------------------------
#
# @dataclass(frozen=True, slots=True)
# class ComplexityResult:
#     complex_multiplies: int
#     complex_adds: int
#     memory_bytes: int
#     latency_samples: int
#     latency_seconds: float
#     method: str
#
# @dataclass(frozen=True, slots=True)
# class ThroughputResult:
#     information_bits_per_symbol: float
#     coded_bits_per_symbol: float
#     spectral_efficiency_bps_hz: float
#     effective_rate_after_papr: float

# ----- Stage 4 : Serialization & Experiment Collections ---------------------
#
# @dataclass(slots=True)
# class ExperimentCollection:
#     results: List[ExperimentResult] = field(default_factory=list)
#     title: str = ""
#
#     def add(self, result: ExperimentResult) -> None:
#         self.results.append(result)
#
# def save_experiment(...): ...
# def load_experiment(...): ...


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Array aliases
    "RealArray",
    "ComplexArray",
    "BitArray",
    "IntArray",
    # Enumerations (Stage 1)
    "ModulationType",
    "ChannelType",
    "EqualizerType",
    "PAPRMethod",
    "CodingType",
    "InterleavingType",
    "FFTNormalization",
    "SNRDefinition",
    "MappingType",
    "Units",
    # Signal containers
    "OFDMGrid",
    "OFDMSignal",
    "TransmitFrame",
    "ReceiveFrame",
    "ChannelOutput",
    # Metrics
    "PAPRResult",
    "CCDFResult",
    "PAPRStatistics",
    "BERResult",
    "EVMResult",
    "PSDResult",
    "ConstellationSnapshot",
    # Configuration & metadata
    "ConfigSnapshot",
    "SimulationMetadata",
    "ExperimentResult",
    # Validation helpers
    "validate_bits",
    "validate_complex_signal",
    "validate_probability",
    "validate_positive_integer",
    "validate_non_negative",
    "validate_snr_db",
    "validate_fft_size",
    "validate_oversampling",
    # Utility functions
    "db_to_linear",
    "linear_to_db",
    "safe_mean_power",
    "safe_peak_power",
    "compute_papr_linear",
    "make_papr_result",
    "bits_to_int",
    "int_to_bits",
    "numpy_fft_norm",
    # Module constants
    "DEFAULT_FFT_SIZE",
    "DEFAULT_OVERSAMPLING",
    "DEFAULT_CP_LENGTH",
    "DEFAULT_SEED",
    "DEFAULT_OFDM_BLOCKS",
    "CCDF_REPORT_PROBABILITIES",
    "ANALYTICAL_CCDF_ALPHA",
]


# =============================================================================
# Module-level constants (convenience)
# =============================================================================

DEFAULT_FFT_SIZE: int = 256
DEFAULT_OVERSAMPLING: int = 4
DEFAULT_CP_LENGTH: int = 16          # original-rate samples
DEFAULT_SEED: int = 42
DEFAULT_OFDM_BLOCKS: int = 100_000

# Probability points used for CCDF reporting in the Research Baseline
CCDF_REPORT_PROBABILITIES: Tuple[float, ...] = (1e-1, 1e-2, 1e-3, 1e-4)

# Analytical CCDF correction factor commonly used in the literature
# for oversampled OFDM (α ≈ 2.8)
ANALYTICAL_CCDF_ALPHA: float = 2.8
