"""
OFDM LinkSim - Channel Models
=============================

Propagation, fading, and additive-noise stage of the OFDM link.

Pipeline
--------
    TransmitFrame.waveform
        │
        ▼
    Channel Model
        │
        ├── AWGN
        ├── Rayleigh + AWGN
        └── Rician + AWGN
        │
        ▼
    ChannelOutput

Supported channel models
------------------------
- AWGN
    Additive white Gaussian noise only.

- Rayleigh
    Flat Rayleigh fading + complex AWGN.

- Rician
    Flat Rician fading + complex AWGN.

Design principles
-----------------
1. All randomness MUST originate from the injected ``numpy.random.Generator``.
2. The global NumPy random state is never used.
3. Channel functions operate on complex baseband samples.
4. Fading coefficients are unit-power by construction.
5. ChannelOutput is always returned through the validated project type.
6. The public ``apply_channel`` API remains stable for pipeline integration.
7. The implementation is intentionally modular so that future extensions
   such as Doppler, frequency-selective multipath, and time-varying channels
   can be added without redesigning the public pipeline API.

Research notes
--------------
For a complex AWGN process:

    n ~ CN(0, sigma_n^2)

the total complex noise power is

    E[|n|^2] = sigma_n^2

and therefore each real/imaginary component has variance

    sigma_n^2 / 2.

Rayleigh fading is generated as:

    h ~ CN(0, 1)

so:

    E[|h|^2] = 1.

Rician fading is generated as:

    h = sqrt(K/(K+1)) * exp(j*phi)
        + sqrt(1/(K+1)) * g

where:

    g ~ CN(0, 1)

and:

    K = P_LOS / P_scatter.

This guarantees approximately unit average fading power.
"""

from __future__ import annotations

from typing import Optional, Literal

import numpy as np

from ofdm_linksim.core.types import (
    ComplexArray,
    TransmitFrame,
    ChannelOutput,
    ChannelType,
    SNRDefinition,
    OFDMSignal,
    db_to_linear,
    validate_complex_signal,
    validate_snr_db,
    safe_mean_power,
)


# ============================================================================
# Constants
# ============================================================================

_EPSILON = np.finfo(np.float64).eps

NoiseReference = Literal["received", "transmit"]


# ============================================================================
# Validation helpers
# ============================================================================


def _validate_rng(rng: np.random.Generator) -> None:
    """
    Validate the injected random-number generator.

    The simulator deliberately requires an explicit Generator so that
    experiments remain reproducible and independent across simulation
    streams.
    """
    if not isinstance(rng, np.random.Generator):
        raise TypeError(
            "rng must be an instance of numpy.random.Generator."
        )


def _validate_positive_integer(
    value: Optional[int],
    name: str,
) -> None:
    """Validate an optional positive integer parameter."""
    if value is None:
        return

    if not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero.")


def _validate_k_factor(k_factor_db: float) -> None:
    """
    Validate a Rician K-factor.

    K is a power ratio and therefore cannot be negative in linear scale.
    In dB representation this means finite values are accepted, while
    -inf is rejected because it is not a useful Rician configuration
    for this implementation.
    """
    if not isinstance(k_factor_db, (int, float, np.integer, np.floating)):
        raise TypeError("k_factor_db must be a real number.")

    if not np.isfinite(k_factor_db):
        raise ValueError("k_factor_db must be finite.")


def _validate_noise_reference(
    noise_reference: NoiseReference,
) -> None:
    """Validate the reference used to derive AWGN power."""
    if noise_reference not in ("received", "transmit"):
        raise ValueError(
            "noise_reference must be either 'received' or 'transmit'."
        )


# ============================================================================
# Signal helpers
# ============================================================================


def _signal_power(x: ComplexArray) -> float:
    """
    Return average complex-signal power.

    The project-level ``safe_mean_power`` helper is used so that power
    computation follows the same numerical conventions as the rest of
    OFDM-LinkSim.
    """
    validate_complex_signal(x)

    power = float(safe_mean_power(x))

    if not np.isfinite(power):
        raise ValueError("Signal power is not finite.")

    return power


def _ensure_nonzero_signal_power(
    signal_power: float,
) -> None:
    """
    Reject a zero-power signal.

    A zero-power waveform cannot define a meaningful SNR-based noise
    level because:

        P_noise = P_signal / SNR

    would result in zero noise regardless of the requested SNR.
    """
    if signal_power <= _EPSILON:
        raise ValueError(
            "Signal power must be greater than zero for channel simulation."
        )


# ============================================================================
# AWGN helpers
# ============================================================================


def _awgn_noise(
    shape: tuple[int, ...],
    noise_power: float,
    rng: np.random.Generator,
) -> ComplexArray:
    """
    Generate circularly symmetric complex AWGN.

    Parameters
    ----------
    shape:
        Output shape.

    noise_power:
        Total complex noise power E[|n|²].

    rng:
        Explicit NumPy random generator.

    Returns
    -------
    ComplexArray
        Complex Gaussian noise with approximately the requested power.
    """
    _validate_rng(rng)

    if not np.isfinite(noise_power):
        raise ValueError("noise_power must be finite.")

    if noise_power < 0.0:
        raise ValueError("noise_power cannot be negative.")

    if noise_power == 0.0:
        return np.zeros(shape, dtype=np.complex128)

    sigma = np.sqrt(noise_power / 2.0)

    real = rng.standard_normal(shape)
    imag = rng.standard_normal(shape)

    noise = sigma * (real + 1j * imag)

    return np.asarray(noise, dtype=np.complex128)


def _noise_power_from_snr(
    signal_power: float,
    snr_db: float,
) -> float:
    """
    Convert signal power and SNR(dB) into AWGN power.

    Definition:

        SNR_linear = 10^(SNR_dB / 10)

        P_noise = P_signal / SNR_linear
    """
    if not np.isfinite(signal_power):
        raise ValueError("signal_power must be finite.")

    if signal_power < 0.0:
        raise ValueError("signal_power cannot be negative.")

    validate_snr_db(snr_db)

    snr_linear = float(db_to_linear(snr_db))

    if not np.isfinite(snr_linear) or snr_linear <= 0.0:
        raise ValueError(
            "SNR linear value must be finite and positive."
        )

    noise_power = signal_power / snr_linear

    if not np.isfinite(noise_power):
        raise ValueError("Calculated noise power is not finite.")

    return float(noise_power)


# ============================================================================
# Fading helpers
# ============================================================================


def _rayleigh_gain(
    n: int,
    rng: np.random.Generator,
    *,
    normalize_power: bool = False,
) -> ComplexArray:
    """
    Generate flat Rayleigh fading coefficients.

    Distribution
    ------------
        h ~ CN(0, 1)

    Therefore:

        E[|h|²] = 1

    Parameters
    ----------
    n:
        Number of fading coefficients.

    rng:
        Explicit random generator.

    normalize_power:
        If True, normalize the generated realization to exactly unit
        average power. This is useful when deterministic Monte-Carlo
        comparisons require realization-level power normalization.
    """
    _validate_positive_integer(n, "n")
    _validate_rng(rng)

    real = rng.standard_normal(n)
    imag = rng.standard_normal(n)

    h = (real + 1j * imag) / np.sqrt(2.0)
    h = np.asarray(h, dtype=np.complex128)

    if normalize_power:
        power = float(np.mean(np.abs(h) ** 2))

        if power > _EPSILON:
            h = h / np.sqrt(power)

    return h


def _rician_gain(
    n: int,
    k_factor_db: float,
    rng: np.random.Generator,
    *,
    los_phase: Optional[float] = None,
    normalize_power: bool = False,
) -> ComplexArray:
    """
    Generate flat Rician fading coefficients.

    Model
    -----
        h =
            sqrt(K/(K+1)) * exp(j*phi)
            +
            sqrt(1/(K+1)) * g

    where:

        g ~ CN(0,1)

    and:

        K = P_LOS / P_scatter.

    Parameters
    ----------
    n:
        Number of fading coefficients.

    k_factor_db:
        Rician K-factor in dB.

    rng:
        Explicit random generator.

    los_phase:
        Optional deterministic LOS phase in radians.

        If None, every coefficient receives an independent random LOS
        phase. This preserves the behavior of the original implementation.

    normalize_power:
        If True, normalize the generated realization to exactly unit
        average power.
    """
    _validate_positive_integer(n, "n")
    _validate_rng(rng)
    _validate_k_factor(k_factor_db)

    k_linear = float(db_to_linear(k_factor_db))

    if not np.isfinite(k_linear) or k_linear < 0.0:
        raise ValueError(
            "Rician K-factor must map to a finite non-negative linear value."
        )

    los_scale = np.sqrt(k_linear / (k_linear + 1.0))
    scatter_scale = np.sqrt(1.0 / (k_linear + 1.0))

    if los_phase is None:
        phase = rng.uniform(
            0.0,
            2.0 * np.pi,
            size=n,
        )
    else:
        if not isinstance(
            los_phase,
            (int, float, np.integer, np.floating),
        ):
            raise TypeError("los_phase must be a real number.")

        if not np.isfinite(los_phase):
            raise ValueError("los_phase must be finite.")

        phase = np.full(n, float(los_phase))

    los = los_scale * np.exp(1j * phase)

    scatter = scatter_scale * (
        rng.standard_normal(n)
        + 1j * rng.standard_normal(n)
    ) / np.sqrt(2.0)

    h = np.asarray(los + scatter, dtype=np.complex128)

    if normalize_power:
        power = float(np.mean(np.abs(h) ** 2))

        if power > _EPSILON:
            h = h / np.sqrt(power)

    return h


# ============================================================================
# Fading expansion helpers
# ============================================================================


def _build_flat_fading(
    signal_size: int,
    rng: np.random.Generator,
    *,
    channel_type: ChannelType,
    per_symbol: bool,
    samples_per_symbol: Optional[int],
    k_factor_db: float,
    los_phase: Optional[float],
    normalize_fading: bool,
) -> ComplexArray:
    """
    Construct a sample-domain flat-fading coefficient vector.

    ``per_symbol=True`` means one coefficient is generated for every
    OFDM symbol and repeated across all samples belonging to that symbol.

    ``per_symbol=False`` means a single coefficient is applied to the
    complete burst.
    """
    if signal_size <= 0:
        raise ValueError("signal_size must be greater than zero.")

    if per_symbol:
        _validate_positive_integer(
            samples_per_symbol,
            "samples_per_symbol",
        )

        assert samples_per_symbol is not None

        if signal_size % samples_per_symbol != 0:
            raise ValueError(
                "Signal length is not a multiple of samples_per_symbol."
            )

        n_symbols = signal_size // samples_per_symbol
    else:
        n_symbols = 1

    if channel_type is ChannelType.RAYLEIGH:
        symbol_gain = _rayleigh_gain(
            n_symbols,
            rng,
            normalize_power=normalize_fading,
        )

    elif channel_type is ChannelType.RICIAN:
        symbol_gain = _rician_gain(
            n_symbols,
            k_factor_db,
            rng,
            los_phase=los_phase,
            normalize_power=normalize_fading,
        )

    else:
        raise ValueError(
            f"Fading generation is not supported for "
            f"channel_type={channel_type!r}."
        )

    if per_symbol:
        return np.repeat(
            symbol_gain,
            samples_per_symbol,
        ).astype(np.complex128, copy=False)

    return np.full(
        signal_size,
        symbol_gain[0],
        dtype=np.complex128,
    )


# ============================================================================
# Public channel primitives
# ============================================================================


def apply_awgn(
    signal: ComplexArray,
    snr_db: float,
    rng: np.random.Generator,
) -> tuple[ComplexArray, float]:
    """
    Apply complex AWGN to a baseband signal.

    Parameters
    ----------
    signal:
        Complex input waveform.

    snr_db:
        Requested SNR in dB.

    rng:
        Explicit random-number generator.

    Returns
    -------
    noisy_signal:
        Signal after AWGN.

    noise_power:
        Theoretical average noise power used to generate the realization.
    """
    validate_complex_signal(signal)
    validate_snr_db(snr_db)
    _validate_rng(rng)

    sig = np.asarray(signal, dtype=np.complex128)

    signal_power = _signal_power(sig)
    _ensure_nonzero_signal_power(signal_power)

    noise_power = _noise_power_from_snr(
        signal_power,
        snr_db,
    )

    noise = _awgn_noise(
        sig.shape,
        noise_power,
        rng,
    )

    return sig + noise, noise_power


def apply_rayleigh(
    signal: ComplexArray,
    snr_db: float,
    rng: np.random.Generator,
    *,
    per_symbol: bool = True,
    samples_per_symbol: Optional[int] = None,
    normalize_fading: bool = False,
    noise_reference: NoiseReference = "received",
) -> tuple[ComplexArray, float, ComplexArray]:
    """
    Apply flat Rayleigh fading followed by complex AWGN.

    Parameters
    ----------
    signal:
        Complex baseband waveform.

    snr_db:
        Requested SNR in dB.

    rng:
        Explicit random-number generator.

    per_symbol:
        Generate one independent fading coefficient per OFDM symbol.

    samples_per_symbol:
        Number of time-domain samples in one OFDM symbol.

    normalize_fading:
        Normalize the generated fading realization to unit average power.

    noise_reference:
        ``"received"`` preserves the original implementation behavior:
        AWGN power is calculated from the faded signal power.

        ``"transmit"`` calculates AWGN power from the original signal
        power. This mode is useful for experiments where SNR is defined
        relative to the transmitted waveform.

    Returns
    -------
    faded_plus_noise, noise_power, channel_gain
    """
    validate_complex_signal(signal)
    validate_snr_db(snr_db)
    _validate_rng(rng)
    _validate_noise_reference(noise_reference)

    sig = np.asarray(signal, dtype=np.complex128).ravel()

    transmit_power = _signal_power(sig)
    _ensure_nonzero_signal_power(transmit_power)

    h = _build_flat_fading(
        sig.size,
        rng,
        channel_type=ChannelType.RAYLEIGH,
        per_symbol=per_symbol,
        samples_per_symbol=samples_per_symbol,
        k_factor_db=3.0,
        los_phase=None,
        normalize_fading=normalize_fading,
    )

    faded = sig * h

    if noise_reference == "received":
        reference_power = _signal_power(faded)
    else:
        reference_power = transmit_power

    _ensure_nonzero_signal_power(reference_power)

    noise_power = _noise_power_from_snr(
        reference_power,
        snr_db,
    )

    noise = _awgn_noise(
        faded.shape,
        noise_power,
        rng,
    )

    return (
        faded + noise,
        noise_power,
        h,
    )


def apply_rician(
    signal: ComplexArray,
    snr_db: float,
    rng: np.random.Generator,
    *,
    k_factor_db: float = 3.0,
    per_symbol: bool = True,
    samples_per_symbol: Optional[int] = None,
    los_phase: Optional[float] = None,
    normalize_fading: bool = False,
    noise_reference: NoiseReference = "received",
) -> tuple[ComplexArray, float, ComplexArray]:
    """
    Apply flat Rician fading followed by complex AWGN.

    Parameters
    ----------
    signal:
        Complex baseband waveform.

    snr_db:
        Requested SNR in dB.

    rng:
        Explicit random-number generator.

    k_factor_db:
        Rician K-factor in dB.

    per_symbol:
        Generate one independent fading coefficient per OFDM symbol.

    samples_per_symbol:
        Number of samples in one OFDM symbol.

    los_phase:
        Optional fixed LOS phase in radians.

    normalize_fading:
        Normalize the generated realization to unit average power.

    noise_reference:
        ``"received"`` uses the faded waveform power.

        ``"transmit"`` uses the original transmitted waveform power.

    Returns
    -------
    faded_plus_noise, noise_power, channel_gain
    """
    validate_complex_signal(signal)
    validate_snr_db(snr_db)
    _validate_rng(rng)
    _validate_k_factor(k_factor_db)
    _validate_noise_reference(noise_reference)

    sig = np.asarray(signal, dtype=np.complex128).ravel()

    transmit_power = _signal_power(sig)
    _ensure_nonzero_signal_power(transmit_power)

    h = _build_flat_fading(
        sig.size,
        rng,
        channel_type=ChannelType.RICIAN,
        per_symbol=per_symbol,
        samples_per_symbol=samples_per_symbol,
        k_factor_db=k_factor_db,
        los_phase=los_phase,
        normalize_fading=normalize_fading,
    )

    faded = sig * h

    if noise_reference == "received":
        reference_power = _signal_power(faded)
    else:
        reference_power = transmit_power

    _ensure_nonzero_signal_power(reference_power)

    noise_power = _noise_power_from_snr(
        reference_power,
        snr_db,
    )

    noise = _awgn_noise(
        faded.shape,
        noise_power,
        rng,
    )

    return (
        faded + noise,
        noise_power,
        h,
    )


# ============================================================================
# High-level pipeline entry point
# ============================================================================


def apply_channel(
    transmit_frame: TransmitFrame,
    *,
    snr_db: float,
    rng: np.random.Generator,
    channel_type: ChannelType = ChannelType.AWGN,
    k_factor_db: float = 3.0,
    per_symbol_fading: bool = True,
    snr_definition: SNRDefinition = SNRDefinition.EsN0,
    normalize_fading: bool = False,
    noise_reference: NoiseReference = "received",
    los_phase: Optional[float] = None,
    **kwargs,
) -> ChannelOutput:
    """
    Apply the selected channel model to a TransmitFrame.

    This is the main pipeline-facing entry point.

    Parameters
    ----------
    transmit_frame:
        Output of the OFDM modulation stage.

    snr_db:
        Operating SNR in dB.

    rng:
        Explicit RNG belonging to the channel/fading stream.

    channel_type:
        ChannelType.AWGN, ChannelType.RAYLEIGH, or ChannelType.RICIAN.

    k_factor_db:
        Rician K-factor in dB.

    per_symbol_fading:
        If True, one independent fading coefficient is generated for
        each OFDM symbol.

    snr_definition:
        Project-level SNR definition.

        The current channel implementation keeps this parameter in the
        public API so the pipeline can explicitly communicate the SNR
        convention. Es/N0 remains the default project convention.

    normalize_fading:
        Normalize generated fading realization to unit average power.

    noise_reference:
        ``"received"`` preserves the historical implementation behavior.

        ``"transmit"`` makes the requested SNR relative to the transmitted
        waveform power.

    los_phase:
        Optional deterministic Rician LOS phase.

    kwargs:
        Reserved for future channel extensions.

    Returns
    -------
    ChannelOutput
        Validated channel-stage output.

    Notes
    -----
    The current project supports flat fading only.

    Future channel extensions can use ``kwargs`` for features such as:

        - Doppler frequency
        - coherence time
        - multipath taps
        - path delays
        - path powers
        - time-varying fading
        - frequency-selective fading
        - channel estimation metadata

    without changing the pipeline-facing function name.
    """
    if not isinstance(transmit_frame, TransmitFrame):
        raise TypeError(
            "transmit_frame must be a TransmitFrame instance."
        )

    _validate_rng(rng)
    validate_snr_db(snr_db)
    _validate_k_factor(k_factor_db)
    _validate_noise_reference(noise_reference)

    waveform: OFDMSignal = transmit_frame.waveform

    samples = np.asarray(
        waveform.samples,
        dtype=np.complex128,
    )

    validate_complex_signal(samples)

    original_shape = samples.shape

    # Determine one OFDM symbol's sample count.
    #
    # CP is included in the channel-domain symbol length when present.
    samples_per_symbol = (
        waveform.total_length_per_symbol
        if waveform.cp_included
        else waveform.useful_length
    )

    # Keep the public SNR convention explicit even though the current
    # Es/N0 implementation uses waveform power directly.
    _ = snr_definition

    # ------------------------------------------------------------------
    # AWGN
    # ------------------------------------------------------------------

    if channel_type is ChannelType.AWGN:
        noisy, noise_power = apply_awgn(
            samples,
            snr_db,
            rng,
        )

        gain = None

    # ------------------------------------------------------------------
    # Rayleigh
    # ------------------------------------------------------------------

    elif channel_type is ChannelType.RAYLEIGH:
        noisy, noise_power, gain = apply_rayleigh(
            samples,
            snr_db,
            rng,
            per_symbol=per_symbol_fading,
            samples_per_symbol=samples_per_symbol,
            normalize_fading=normalize_fading,
            noise_reference=noise_reference,
        )

    # ------------------------------------------------------------------
    # Rician
    # ------------------------------------------------------------------

    elif channel_type is ChannelType.RICIAN:
        noisy, noise_power, gain = apply_rician(
            samples,
            snr_db,
            rng,
            k_factor_db=k_factor_db,
            per_symbol=per_symbol_fading,
            samples_per_symbol=samples_per_symbol,
            los_phase=los_phase,
            normalize_fading=normalize_fading,
            noise_reference=noise_reference,
        )

    # ------------------------------------------------------------------
    # Unsupported
    # ------------------------------------------------------------------

    else:
        raise ValueError(
            f"Unsupported channel type: {channel_type!r}"
        )

    # The primitive fading functions operate on a flattened waveform.
    # Restore the exact input shape before constructing ChannelOutput.
    if noisy.shape != original_shape:
        noisy = np.asarray(
            noisy,
            dtype=np.complex128,
        ).reshape(original_shape)

    # Keep gain aligned with the original waveform shape whenever
    # possible. This is especially useful for multi-dimensional
    # representations used by future pipeline stages.
    if gain is not None and gain.size == samples.size:
        gain = np.asarray(
            gain,
            dtype=np.complex128,
        ).reshape(original_shape)

    # Final numerical safety checks.
    validate_complex_signal(noisy)

    if not np.isfinite(noise_power):
        raise ValueError(
            "Channel produced a non-finite noise power."
        )

    return ChannelOutput(
        signal=noisy,
        snr_db=float(snr_db),
        channel_type=channel_type,
        noise_power=float(noise_power),
        channel_gain=gain,
    )


# ============================================================================
# Pipeline compatibility alias
# ============================================================================

channel = apply_channel


__all__ = [
    "apply_awgn",
    "apply_rayleigh",
    "apply_rician",
    "apply_channel",
    "channel",
]
