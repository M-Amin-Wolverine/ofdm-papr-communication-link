#!/usr/bin/env python3
"""
Stage-1 BER baseline example
============================

Uncoded QPSK OFDM over AWGN — BER at one SNR or a small SNR sweep.

Chain
-----
    random bits → QPSK → OFDM TX → AWGN → OFDM RX → QPSK demod → BER

Usage
-----
    python examples/baseline_ber.py
    python examples/baseline_ber.py --snr 10 --blocks 40
    python examples/baseline_ber.py --sweep 0 20 4 --blocks 30

Requires:

    pip install -e .
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ofdm_linksim.analysis.ber import aggregate_ber, compute_ber
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
from ofdm_linksim.utils.random import make_stream_rngs


FFT_SIZE = DEFAULT_FFT_SIZE
OVERSAMPLING = DEFAULT_OVERSAMPLING
CP_LENGTH = DEFAULT_CP_LENGTH
N_DATA = 192
MOD = ModulationType.QPSK


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OFDM-PAPR Stage-1 BER baseline")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--snr", type=float, default=12.0, help="Single SNR (dB)")
    p.add_argument(
        "--sweep",
        nargs=3,
        type=float,
        metavar=("START", "STOP", "STEP"),
        default=None,
        help="SNR sweep: start stop step (inclusive-ish via arange)",
    )
    p.add_argument("--blocks", type=int, default=40, help="OFDM symbols per SNR point")
    p.add_argument("--fft-size", type=int, default=FFT_SIZE)
    p.add_argument("--n-data", type=int, default=N_DATA)
    p.add_argument("--cp", type=int, default=CP_LENGTH)
    p.add_argument("--oversampling", type=int, default=OVERSAMPLING)
    return p.parse_args()


def snr_grid(args: argparse.Namespace) -> List[float]:
    if args.sweep is None:
        return [float(args.snr)]
    start, stop, step = args.sweep
    if step <= 0:
        raise ValueError("sweep STEP must be positive.")
    vals = list(np.arange(start, stop + 0.5 * step, step, dtype=np.float64))
    return [float(v) for v in vals]


def run_one_snr(
    *,
    seed: int,
    snr_db: float,
    n_blocks: int,
    fft_size: int,
    n_data: int,
    cp_length: int,
    oversampling: int,
) -> dict:
    streams = make_stream_rngs(seed)
    rng_src = streams["source"]
    rng_ch = streams["channel"]

    bps = bits_per_symbol(MOD)
    n_mod_symbols = n_data * n_blocks
    n_bits = n_mod_symbols * bps

    source_bits = generate_random_bits(n_bits, seed=seed, rng=rng_src)
    tx_symbols = modulate(source_bits, mod=MOD)

    tx_frame = modulate_ofdm(
        tx_symbols,
        source_bits=source_bits,
        coded_bits=source_bits,
        interleaved_bits=source_bits,
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cp_length,
        n_data=n_data,
        n_pilots=0,
        mapping=MappingType.SYMMETRIC,
    )

    channel_out = apply_channel(
        tx_frame,
        snr_db=snr_db,
        rng=rng_ch,
        channel_type=ChannelType.AWGN,
    )

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

    rx_symbols = np.asarray(demod.equalized_symbols, dtype=np.complex128).ravel()
    n_sym = min(rx_symbols.size, tx_symbols.size)
    rx_symbols = rx_symbols[:n_sym]

    rx_bits = demodulate(rx_symbols, mod=MOD)
    n_bit = min(rx_bits.size, source_bits.size)
    ber = compute_ber(source_bits[:n_bit], rx_bits[:n_bit], snr_db=snr_db)

    return {
        "snr_db": float(snr_db),
        "ber": float(ber.ber),
        "bit_errors": int(ber.bit_errors),
        "total_bits": int(ber.total_bits),
        "n_blocks": int(n_blocks),
        "n_bits": int(n_bit),
    }


def main() -> int:
    args = parse_args()
    grid = snr_grid(args)

    rows = []
    for snr in grid:
        # independent stream offset per SNR for diversity while staying reproducible
        seed_i = int(args.seed + int(round(snr * 1000)) % 100000)
        row = run_one_snr(
            seed=seed_i,
            snr_db=snr,
            n_blocks=args.blocks,
            fft_size=args.fft_size,
            n_data=args.n_data,
            cp_length=args.cp,
            oversampling=args.oversampling,
        )
        rows.append(row)

    print("=" * 64)
    print("OFDM-PAPR-LinkSim — Stage-1 BER baseline (QPSK, AWGN, uncoded)")
    print("=" * 64)
    print(f"  base seed     : {args.seed}")
    print(f"  modulation    : {MOD.value}")
    print(f"  channel       : {ChannelType.AWGN.value}")
    print(f"  OFDM blocks   : {args.blocks}  (per SNR point)")
    print(f"  FFT / data    : {args.fft_size} / {args.n_data}")
    print("-" * 64)
    print(f"  {'SNR [dB]':>10}  {'BER':>12}  {'errors':>10}  {'bits':>10}")
    print("-" * 64)
    for r in rows:
        print(
            f"  {r['snr_db']:10.2f}  {r['ber']:12.4e}  "
            f"{r['bit_errors']:10d}  {r['total_bits']:10d}"
        )
    print("=" * 64)

    if len(rows) > 1:
        # rough monotonicity hint (not a formal test)
        bers = [r["ber"] for r in rows]
        if all(bers[i] >= bers[i + 1] - 1e-15 for i in range(len(bers) - 1)):
            print("  note: BER is non-increasing across the sweep (good sign).")
        else:
            print("  note: BER not strictly decreasing — try more --blocks.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
