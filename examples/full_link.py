#!/usr/bin/env python3
"""
Stage-1 full link example
=========================

End-to-end uncoded QPSK OFDM over AWGN:

    random bits
        → QPSK
        → OFDM modulator
        → PAPR (method = none)
        → AWGN channel
        → OFDM demodulator
        → QPSK demodulator
        → BER / EVM / PAPR report

Usage
-----
    python examples/full_link.py
    python examples/full_link.py --snr 12 --blocks 50 --seed 7

Requires an editable install from the repo root:

    pip install -e .
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Allow running without install if repo root is on PYTHONPATH
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

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
)
from ofdm_linksim.modulation import bits_per_symbol, demodulate, modulate
from ofdm_linksim.ofdm_demodulator import demodulate_ofdm
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.utils.random import (
    channel_rng,
    make_stream_rngs,
    papr_rng,
    source_rng,
)

from papr_methods.none import apply_none


# ---------------------------------------------------------------------------
# Defaults aligned with Research Baseline
# ---------------------------------------------------------------------------

FFT_SIZE = DEFAULT_FFT_SIZE          # 256
OVERSAMPLING = DEFAULT_OVERSAMPLING  # 4
CP_LENGTH = DEFAULT_CP_LENGTH        # 16 (original-rate samples)
N_DATA = 192                         # baseline data subcarriers
N_PILOTS = 0                         # Stage-1: no pilots
MOD = ModulationType.QPSK


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OFDM-PAPR-LinkSim Stage-1 full link")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--snr", type=float, default=20.0, help="SNR in dB (Es/N0)")
    p.add_argument(
        "--blocks",
        type=int,
        default=20,
        help="Number of OFDM symbols (keep small for a quick demo)",
    )
    p.add_argument("--fft-size", type=int, default=FFT_SIZE)
    p.add_argument("--n-data", type=int, default=N_DATA)
    p.add_argument("--cp", type=int, default=CP_LENGTH)
    p.add_argument("--oversampling", type=int, default=OVERSAMPLING)
    return p.parse_args()


def run_full_link(
    *,
    seed: int,
    snr_db: float,
    n_blocks: int,
    fft_size: int,
    n_data: int,
    cp_length: int,
    oversampling: int,
) -> dict:
    """Run one Stage-1 link and return a plain summary dict."""
    if n_blocks <= 0:
        raise ValueError("n_blocks must be positive.")
    if n_data <= 0 or n_data >= fft_size:
        raise ValueError("n_data must be in (0, fft_size).")

    streams = make_stream_rngs(seed)
    rng_src = streams["source"]
    rng_ch = streams["channel"]
    rng_papr = streams["papr"]

    bps = bits_per_symbol(MOD)
    n_mod_symbols = n_data * n_blocks
    n_bits = n_mod_symbols * bps

    # ------------------------------------------------------------------
    # TX
    # ------------------------------------------------------------------
    source_bits = generate_random_bits(n_bits, seed=seed, rng=rng_src)
    # Stage-1 identity coding / interleaving
    coded_bits = source_bits.copy()
    interleaved_bits = coded_bits.copy()

    tx_symbols = modulate(interleaved_bits, mod=MOD)

    tx_frame = modulate_ofdm(
        tx_symbols,
        source_bits=source_bits,
        coded_bits=coded_bits,
        interleaved_bits=interleaved_bits,
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cp_length,
        n_data=n_data,
        n_pilots=N_PILOTS,
        mapping=MappingType.SYMMETRIC,
    )

    # ------------------------------------------------------------------
    # PAPR (method = none) — useful samples only
    # ------------------------------------------------------------------
    papr_proc = apply_none(tx_frame, rng=rng_papr)
    papr_result = papr_proc.papr

    # ------------------------------------------------------------------
    # Channel (AWGN)
    # ------------------------------------------------------------------
    channel_out = apply_channel(
        tx_frame,
        snr_db=snr_db,
        rng=rng_ch,
        channel_type=ChannelType.AWGN,
    )

    # ------------------------------------------------------------------
    # RX
    # ------------------------------------------------------------------
    demod = demodulate_ofdm(
        channel_out.signal,
        data_indices=tx_frame.ofdm_grid.data_indices,
        pilot_indices=tx_frame.ofdm_grid.pilot_indices,
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cp_length,
        n_symbols=tx_frame.waveform.n_symbols,
        cp_included=tx_frame.waveform.cp_included,
    )

    # equalized_symbols are the recovered data-bearing constellation points
    rx_symbols = np.asarray(demod.equalized_symbols, dtype=np.complex128).ravel()
    # align lengths (safety)
    n = min(rx_symbols.size, tx_symbols.size)
    rx_symbols = rx_symbols[:n]
    tx_ref = np.asarray(tx_symbols, dtype=np.complex128).ravel()[:n]

    rx_bits = demodulate(rx_symbols, mod=MOD)
    n_bit = min(rx_bits.size, source_bits.size)
    ber = compute_ber(source_bits[:n_bit], rx_bits[:n_bit], snr_db=snr_db)
    evm = compute_evm(tx_ref, rx_symbols)

    return {
        "seed": seed,
        "snr_db": float(snr_db),
        "n_blocks": int(n_blocks),
        "fft_size": int(fft_size),
        "n_data": int(n_data),
        "n_bits": int(n_bits),
        "modulation": MOD.value,
        "channel": ChannelType.AWGN.value,
        "papr_method": "none",
        "papr_db": float(papr_result.papr_db),
        "papr_linear": float(papr_result.papr_linear),
        "n_samples_papr": int(papr_result.n_samples_used),
        "ber": float(ber.ber),
        "bit_errors": int(ber.bit_errors),
        "total_bits": int(ber.total_bits),
        "rms_evm_percent": float(getattr(evm, "rms_evm_percent", getattr(evm, "rms_evm", 0.0) * 100.0)),
    }


def main() -> int:
    args = parse_args()
    try:
        summary = run_full_link(
            seed=args.seed,
            snr_db=args.snr,
            n_blocks=args.blocks,
            fft_size=args.fft_size,
            n_data=args.n_data,
            cp_length=args.cp,
            oversampling=args.oversampling,
        )
    except Exception as exc:
        print(f"[full_link] FAILED: {exc}", file=sys.stderr)
        raise

    print("=" * 64)
    print("OFDM-PAPR-LinkSim — Stage-1 full link")
    print("=" * 64)
    print(f"  seed            : {summary['seed']}")
    print(f"  modulation      : {summary['modulation']}")
    print(f"  channel         : {summary['channel']}")
    print(f"  SNR (dB)        : {summary['snr_db']:.2f}")
    print(f"  OFDM blocks     : {summary['n_blocks']}")
    print(f"  FFT size        : {summary['fft_size']}")
    print(f"  data tones      : {summary['n_data']}")
    print(f"  bits            : {summary['n_bits']}")
    print("-" * 64)
    print(f"  PAPR            : {summary['papr_db']:.4f} dB  "
          f"(linear={summary['papr_linear']:.4f}, "
          f"N={summary['n_samples_papr']})")
    print(f"  BER             : {summary['ber']:.6e}  "
          f"({summary['bit_errors']}/{summary['total_bits']})")
    print(f"  RMS EVM         : {summary['rms_evm_percent']:.4f} %")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
