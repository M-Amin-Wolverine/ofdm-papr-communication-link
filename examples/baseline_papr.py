#!/usr/bin/env python3
"""
Stage-1 PAPR baseline example
=============================

Generate uncoded QPSK-OFDM waveforms and measure PAPR with:

- method ``none``     (locked scientific reference)
- method ``clipping`` (optional comparison)

PAPR is always evaluated on useful (non-CP) samples.

Usage
-----
    python examples/baseline_papr.py
    python examples/baseline_papr.py --blocks 200 --clip 1.4 --seed 42

Requires:

    pip install -e .
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ofdm_linksim.core.types import (
    DEFAULT_CP_LENGTH,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERSAMPLING,
    DEFAULT_SEED,
    MappingType,
    ModulationType,
)
from ofdm_linksim.modulation import bits_per_symbol, modulate
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.utils.random import make_stream_rngs

from papr_methods.clipping import apply_clipping
from papr_methods.none import apply_none


FFT_SIZE = DEFAULT_FFT_SIZE
OVERSAMPLING = DEFAULT_OVERSAMPLING
CP_LENGTH = DEFAULT_CP_LENGTH
N_DATA = 192
MOD = ModulationType.QPSK


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OFDM-PAPR baseline (none vs clipping)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--blocks", type=int, default=100, help="Number of OFDM symbols")
    p.add_argument("--fft-size", type=int, default=FFT_SIZE)
    p.add_argument("--n-data", type=int, default=N_DATA)
    p.add_argument("--cp", type=int, default=CP_LENGTH)
    p.add_argument("--oversampling", type=int, default=OVERSAMPLING)
    p.add_argument(
        "--clip",
        type=float,
        default=1.5,
        help="Clipping ratio CR = A / rms (used when --compare-clip)",
    )
    p.add_argument(
        "--compare-clip",
        action="store_true",
        help="Also run hard clipping and print delta PAPR",
    )
    p.add_argument(
        "--collect",
        type=int,
        default=0,
        help="If >0, emit per-block PAPR list length (for CCDF experiments)",
    )
    return p.parse_args()


def build_tx_frame(
    *,
    seed: int,
    n_blocks: int,
    fft_size: int,
    n_data: int,
    cp_length: int,
    oversampling: int,
):
    streams = make_stream_rngs(seed)
    rng_src = streams["source"]
    rng_papr = streams["papr"]

    bps = bits_per_symbol(MOD)
    n_mod_symbols = n_data * n_blocks
    n_bits = n_mod_symbols * bps

    bits = generate_random_bits(n_bits, rng=rng_src)
    symbols = modulate(bits, mod=MOD)

    tx = modulate_ofdm(
        symbols,
        source_bits=bits,
        coded_bits=bits,
        interleaved_bits=bits,
        fft_size=fft_size,
        oversampling=oversampling,
        cyclic_prefix_length=cp_length,
        n_data=n_data,
        n_pilots=0,
        mapping=MappingType.SYMMETRIC,
    )
    return tx, rng_papr


def per_block_papr_db(tx, rng, *, method: str = "none", clipping_ratio: float = 1.5) -> np.ndarray:
    """
    Measure PAPR per OFDM symbol (useful samples only).

    For a quick CCDF-style list without the full analysis module path.
    """
    from ofdm_linksim.papr import get_useful_samples
    from ofdm_linksim.core.types import make_papr_result

    useful = np.asarray(get_useful_samples(tx.waveform), dtype=np.complex128)
    # useful layout: (n_sym, n_fft * L) or flat
    if useful.ndim == 1:
        n_sym = tx.waveform.n_symbols
        n_per = useful.size // n_sym
        useful = useful.reshape(n_sym, n_per)

    if method == "clipping":
        # clip entire useful grid then measure per row
        from papr_methods.clipping import _clip_hard
        from ofdm_linksim.core.types import safe_mean_power

        flat = useful.ravel()
        rms = float(np.sqrt(safe_mean_power(flat)))
        amp = clipping_ratio * rms
        useful = _clip_hard(flat, amp).reshape(useful.shape)

    vals = []
    for row in useful:
        pr = make_papr_result(row.ravel(), cp_excluded=True)
        vals.append(pr.papr_db)
    return np.asarray(vals, dtype=np.float64)


def main() -> int:
    args = parse_args()

    tx, rng_papr = build_tx_frame(
        seed=args.seed,
        n_blocks=args.blocks,
        fft_size=args.fft_size,
        n_data=args.n_data,
        cp_length=args.cp,
        oversampling=args.oversampling,
    )

    # --- reference (none) ---
    ref = apply_none(tx, rng=rng_papr)

    print("=" * 64)
    print("OFDM-PAPR-LinkSim — Stage-1 PAPR baseline")
    print("=" * 64)
    print(f"  seed         : {args.seed}")
    print(f"  modulation   : {MOD.value}")
    print(f"  OFDM blocks  : {args.blocks}")
    print(f"  FFT size     : {args.fft_size}")
    print(f"  data tones   : {args.n_data}")
    print(f"  oversampling : {args.oversampling}")
    print(f"  CP length    : {args.cp} (original-rate samples)")
    print("-" * 64)
    print(f"  [none] PAPR  : {ref.papr.papr_db:.4f} dB  "
          f"(linear={ref.papr.papr_linear:.4f}, "
          f"N={ref.papr.n_samples_used})")

    if args.compare_clip:
        clip = apply_clipping(
            tx,
            clipping_ratio=args.clip,
            mode="hard",
            clip_cp=True,
            rng=rng_papr,
        )
        delta = ref.papr.papr_db - clip.papr.papr_db
        print(f"  [clip] PAPR  : {clip.papr.papr_db:.4f} dB  "
              f"(CR={args.clip}, "
              f"noise_p={clip.meta.get('clip_noise_power', float('nan')):.4e})")
        print(f"  delta PAPR   : {delta:.4f} dB  (none − clip)")

    if args.collect > 0:
        n = min(args.collect, args.blocks)
        # rebuild with n blocks if needed
        if n != args.blocks:
            tx_c, rng_c = build_tx_frame(
                seed=args.seed,
                n_blocks=n,
                fft_size=args.fft_size,
                n_data=args.n_data,
                cp_length=args.cp,
                oversampling=args.oversampling,
            )
        else:
            tx_c, rng_c = tx, rng_papr
        arr = per_block_papr_db(tx_c, rng_c, method="none")
        print("-" * 64)
        print(f"  per-block PAPR (none), n={arr.size}")
        print(f"    mean={arr.mean():.4f} dB  "
              f"median={np.median(arr):.4f} dB  "
              f"max={arr.max():.4f} dB  "
              f"min={arr.min():.4f} dB")

    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
