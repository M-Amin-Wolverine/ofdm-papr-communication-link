"""
Factory / orchestration helpers for OFDM-PAPR-LinkSim
=====================================================

Thin layer that wires:

    parameters / method name
        → building blocks
        → papr_methods registry
        → end-to-end link metrics

Does NOT replace the modular blocks or OFDMChain DI design.
It only removes boilerplate so experiments and scripts stay short.

Typical use
-----------
    from ofdm_linksim.factory import run_link, compare_papr_methods

    result = run_link(method="slm", n_blocks=20, snr_db=12.0, seed=42)
    print(result["papr_db"], result["ber"])

    table = compare_papr_methods(n_blocks=16, seed=1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

import numpy as np

from ofdm_linksim.analysis.ber import compute_ber
from ofdm_linksim.analysis.evm import compute_evm
from ofdm_linksim.channel import apply_channel
from ofdm_linksim.core.types import (
    ChannelType,
    DEFAULT_CP_LENGTH,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERSAMPLING,
    DEFAULT_SEED,
    MappingType,
    ModulationType,
    PAPRMethod,
    TransmitFrame,
)
from ofdm_linksim.modulation import bits_per_symbol, demodulate, modulate
from ofdm_linksim.ofdm_demodulator import demodulate_ofdm
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.utils.random import make_stream_rngs

# Registry
from papr_methods import get_method
from papr_methods.none import apply_none
from papr_methods.clipping import apply_clipping
from papr_methods.slm import apply_slm
from papr_methods.pts import apply_pts
from papr_methods.tone_reservation import apply_tone_reservation
from papr_methods.ace import apply_ace


# ---------------------------------------------------------------------------
# Defaults aligned with Stage-1 research baseline
# ---------------------------------------------------------------------------

_DEFAULT_N_DATA = 192
_DEFAULT_N_PILOTS = 0
_DEFAULT_MOD = ModulationType.QPSK


@dataclass
class LinkParams:
    """Explicit, self-contained parameters for one link run."""

    seed: int = DEFAULT_SEED
    snr_db: float = 20.0
    n_blocks: int = 20
    fft_size: int = DEFAULT_FFT_SIZE
    n_data: int = _DEFAULT_N_DATA
    n_pilots: int = _DEFAULT_N_PILOTS
    cp_length: int = DEFAULT_CP_LENGTH
    oversampling: int = DEFAULT_OVERSAMPLING
    modulation: ModulationType = _DEFAULT_MOD
    mapping: MappingType = MappingType.SYMMETRIC
    channel_type: ChannelType = ChannelType.AWGN
    # PAPR
    method: str = "none"
    papr_kwargs: Dict[str, Any] = field(default_factory=dict)


def _normalize_method(name: str) -> str:
    key = str(name).strip().lower().replace("-", "_")
    aliases = {
        "tr": "tone_reservation",
        "tone_res": "tone_reservation",
        "selected_mapping": "slm",
        "partial_transmit_sequence": "pts",
        "clip": "clipping",
        "identity": "none",
        "off": "none",
    }
    return aliases.get(key, key)


def _apply_papr(
    tx: TransmitFrame,
    method: str,
    rng: np.random.Generator,
    **kwargs: Any,
):
    """
    Dispatch to the concrete apply_* implementation.

    Returns PAPRProcessResult (waveform + papr + meta).
    """
    m = _normalize_method(method)

    if m == "none":
        return apply_none(tx, rng=rng, **kwargs)
    if m == "clipping":
        return apply_clipping(tx, rng=rng, **kwargs)
    if m == "slm":
        return apply_slm(tx, rng=rng, **kwargs)
    if m == "pts":
        return apply_pts(tx, rng=rng, **kwargs)
    if m in {"tone_reservation", "tr"}:
        return apply_tone_reservation(tx, rng=rng, **kwargs)
    if m == "ace":
        return apply_ace(tx, rng=rng, **kwargs)

    # Fallback: registry process() only returns PAPRResult (no waveform).
    # Prefer apply_* paths above for a full link.
    raise ValueError(
        f"Unknown or unsupported PAPR method for full-link factory: {method!r}. "
        f"Supported: none, clipping, slm, pts, tone_reservation, ace."
    )


def build_tx_frame(params: LinkParams, streams: Mapping[str, np.random.Generator]) -> TransmitFrame:
    """Source → modulate → OFDM modulate."""
    bps = bits_per_symbol(params.modulation)
    n_bits = params.n_data * params.n_blocks * bps
    bits = generate_random_bits(n_bits, seed=params.seed, rng=streams["source"])
    symbols = modulate(bits, mod=params.modulation)
    return modulate_ofdm(
        symbols,
        source_bits=bits,
        coded_bits=bits,
        interleaved_bits=bits,
        fft_size=params.fft_size,
        oversampling=params.oversampling,
        cyclic_prefix_length=params.cp_length,
        n_data=params.n_data,
        n_pilots=params.n_pilots,
        mapping=params.mapping,
    )


def run_link(
    *,
    method: str = "none",
    seed: int = DEFAULT_SEED,
    snr_db: float = 20.0,
    n_blocks: int = 20,
    fft_size: int = DEFAULT_FFT_SIZE,
    n_data: int = _DEFAULT_N_DATA,
    cp_length: int = DEFAULT_CP_LENGTH,
    oversampling: int = DEFAULT_OVERSAMPLING,
    modulation: Union[ModulationType, str] = _DEFAULT_MOD,
    channel_type: Union[ChannelType, str] = ChannelType.AWGN,
    papr_kwargs: Optional[Dict[str, Any]] = None,
    **extra_papr: Any,
) -> Dict[str, Any]:
    """
    Run one Stage-1-style end-to-end link with a chosen PAPR method.

    Returns a plain dict with PAPR / BER / EVM and metadata.
    """
    _mod_map = {
        "qpsk": ModulationType.QPSK,
        "16qam": ModulationType.QAM16,
        "qam16": ModulationType.QAM16,
        "64qam": ModulationType.QAM64,
        "qam64": ModulationType.QAM64,
        "256qam": ModulationType.QAM256,
        "qam256": ModulationType.QAM256,
    }
    if isinstance(modulation, str):
        modulation = _mod_map.get(modulation.lower().replace("-", ""), ModulationType.QPSK)
    if not isinstance(modulation, ModulationType):
        modulation = ModulationType.QPSK

    if isinstance(channel_type, str):
        ct = channel_type.strip().upper()
        channel_type = ChannelType[ct] if ct in ChannelType.__members__ else ChannelType.AWGN
    if not isinstance(channel_type, ChannelType):
        channel_type = ChannelType.AWGN

    params = LinkParams(
        seed=seed,
        snr_db=float(snr_db),
        n_blocks=int(n_blocks),
        fft_size=int(fft_size),
        n_data=int(n_data),
        cp_length=int(cp_length),
        oversampling=int(oversampling),
        modulation=modulation,
        channel_type=channel_type,
        method=_normalize_method(method),
        papr_kwargs={**(papr_kwargs or {}), **extra_papr},
    )

    streams = make_stream_rngs(params.seed)
    tx = build_tx_frame(params, streams)

    # PAPR stage (may modify waveform)
    papr_res = _apply_papr(
        tx,
        params.method,
        rng=streams["papr"],
        **params.papr_kwargs,
    )
    # Use processed waveform for the channel when method modified it
    from ofdm_linksim.core.types import OFDMSignal

    if params.method == "none":
        wave_for_channel = tx
    else:
        # Rebuild a lightweight TransmitFrame-compatible path:
        # channel.apply_channel expects TransmitFrame; put processed samples
        # back into a copy of tx.waveform.
        samples = np.asarray(papr_res.waveform, dtype=np.complex128)
        new_wave = OFDMSignal(
            samples=samples,
            fft_size=tx.waveform.fft_size,
            oversampling=tx.waveform.oversampling,
            cyclic_prefix_length=tx.waveform.cyclic_prefix_length,
            cp_included=tx.waveform.cp_included,
            n_symbols=tx.waveform.n_symbols,
        )
        # TransmitFrame is a dataclass – rebuild minimal
        tx_for_ch = TransmitFrame(
            source_bits=tx.source_bits,
            coded_bits=tx.coded_bits,
            interleaved_bits=tx.interleaved_bits,
            modulation_symbols=tx.modulation_symbols,
            ofdm_grid=tx.ofdm_grid,
            waveform=new_wave,
        )
        wave_for_channel = tx_for_ch

    ch_out = apply_channel(
        wave_for_channel,
        channel_type=params.channel_type,
        snr_db=params.snr_db,
        rng=streams["channel"],
    )

    # Demod path: use received signal
    rx_signal = ch_out.signal if hasattr(ch_out, "signal") else ch_out
    # Prefer OFDMSignal if channel returned samples only
    if not isinstance(rx_signal, OFDMSignal):
        rx_signal = OFDMSignal(
            samples=np.asarray(rx_signal, dtype=np.complex128),
            fft_size=tx.waveform.fft_size,
            oversampling=tx.waveform.oversampling,
            cyclic_prefix_length=tx.waveform.cyclic_prefix_length,
            cp_included=tx.waveform.cp_included,
            n_symbols=tx.waveform.n_symbols,
        )

    demod = demodulate_ofdm(
        rx_signal,
        data_indices=tx.ofdm_grid.data_indices,
        pilot_indices=tx.ofdm_grid.pilot_indices,
        fft_size=params.fft_size,
        oversampling=params.oversampling,
        cyclic_prefix_length=params.cp_length,
        n_symbols=params.n_blocks,
    )
    rx_syms = demod.ofdm_grid.get_data_symbols()
    rx_syms = np.asarray(rx_syms, dtype=np.complex128)

    # --- Side-information recovery for SLM / PTS (fair BER) ---
    meta = dict(getattr(papr_res, "meta", {}) or {})
    if params.method == "slm" and meta.get("selected_phases"):
        phases = np.asarray(meta["selected_phases"], dtype=np.complex128)
        # rx_syms shape (n_sym, n_data) or flat
        if rx_syms.ndim == 2 and phases.size == rx_syms.shape[1]:
            rx_syms = rx_syms * np.conj(phases)[np.newaxis, :]
        elif rx_syms.ndim == 1 and phases.size > 0:
            n_data = phases.size
            n_sym = rx_syms.size // n_data
            if n_sym * n_data == rx_syms.size:
                tmp = rx_syms.reshape(n_sym, n_data) * np.conj(phases)[np.newaxis, :]
                rx_syms = tmp
    elif params.method == "pts" and meta.get("selected_phases"):
        # Adjacent partitions over data tones – undo b_v on each sub-block
        phases = np.asarray(meta["selected_phases"], dtype=np.complex128)
        n_sub = len(phases)
        if rx_syms.ndim == 1:
            n_data = params.n_data
            n_sym = rx_syms.size // n_data
            rx2 = rx_syms.reshape(n_sym, n_data)
        else:
            rx2 = rx_syms
            n_data = rx2.shape[1]
        sizes = [n_data // n_sub] * n_sub
        for i in range(n_data % n_sub):
            sizes[i] += 1
        start = 0
        for v, s in enumerate(sizes):
            if abs(phases[v]) > 0:
                rx2[:, start : start + s] = rx2[:, start : start + s] / phases[v]
            start += s
        rx_syms = rx2

    rx_syms_flat = np.asarray(rx_syms).ravel()
    # Align length with TX symbols
    tx_syms = np.asarray(tx.modulation_symbols).ravel()
    n = min(tx_syms.size, rx_syms_flat.size)
    tx_syms = tx_syms[:n]
    rx_syms_flat = rx_syms_flat[:n]

    bits_hat = demodulate(rx_syms_flat, mod=params.modulation)
    src_bits = np.asarray(tx.source_bits).ravel()
    n_bits = min(src_bits.size, bits_hat.size)
    ber_res = compute_ber(src_bits[:n_bits], bits_hat[:n_bits])
    try:
        evm_res = compute_evm(tx_syms, rx_syms_flat)
        evm_rms = float(getattr(evm_res, "rms_evm_percent", getattr(evm_res, "rms_evm", float("nan"))))
    except Exception:
        evm_rms = float("nan")

    return {
        "method": params.method,
        "seed": params.seed,
        "snr_db": params.snr_db,
        "n_blocks": params.n_blocks,
        "fft_size": params.fft_size,
        "n_data": params.n_data,
        "papr_db": float(papr_res.papr.papr_db),
        "papr_linear": float(papr_res.papr.papr_linear),
        "ber": float(getattr(ber_res, "ber", ber_res) if not isinstance(ber_res, float) else ber_res),
        "n_bits": int(n_bits),
        "evm_rms_percent": evm_rms,
        "papr_meta": dict(getattr(papr_res, "meta", {}) or {}),
    }


def compare_papr_methods(
    methods: Optional[Sequence[str]] = None,
    *,
    seed: int = 42,
    n_blocks: int = 16,
    snr_db: float = 15.0,
    **common_kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    Run the same link for several PAPR methods and return a list of result dicts.
    """
    if methods is None:
        methods = [
            "none",
            "clipping",
            "slm",
            "pts",
            "tone_reservation",
            "ace",
        ]

    # Sensible per-method defaults (can be overridden via common_kwargs)
    per_method = {
        "none": {},
        "clipping": {"clipping_ratio": 1.5, "mode": "hard"},
        "slm": {"n_candidates": 16, "phase_set": "bipolar"},
        "pts": {"n_subblocks": 4, "n_candidates": 64, "phase_set": "bipolar", "search": "random"},
        "tone_reservation": {"n_reserved": 12, "clipping_ratio": 1.4, "n_iterations": 10},
        "ace": {"clipping_ratio": 1.4, "n_iterations": 10, "step_size": 0.7},
    }

    rows: List[Dict[str, Any]] = []
    for m in methods:
        kw = {**per_method.get(_normalize_method(m), {}), **common_kwargs}
        # split link kwargs vs papr kwargs
        link_keys = {
            "seed", "snr_db", "n_blocks", "fft_size", "n_data",
            "cp_length", "oversampling", "modulation", "channel_type",
        }
        papr_kw = {k: v for k, v in kw.items() if k not in link_keys}
        link_kw = {k: v for k, v in kw.items() if k in link_keys}
        row = run_link(
            method=m,
            seed=seed,
            n_blocks=n_blocks,
            snr_db=snr_db,
            papr_kwargs=papr_kw,
            **link_kw,
        )
        rows.append(row)
    return rows


def get_papr_processor(method: str):
    """
    Return the registry ``process()`` callable for use as
    ``PipelineComponents.papr_processor``.

    Note: process() returns PAPRResult only (no modified waveform).
    For full-link simulation with waveform modification prefer ``run_link``.
    """
    return get_method(_normalize_method(method))


__all__ = [
    "LinkParams",
    "run_link",
    "compare_papr_methods",
    "build_tx_frame",
    "get_papr_processor",
]
