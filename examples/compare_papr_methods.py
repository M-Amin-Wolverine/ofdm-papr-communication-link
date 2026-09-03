#!/usr/bin/env python3
"""
Compare PAPR reduction methods on the same Stage-1 link.

Usage
-----
    PYTHONPATH=src:. python examples/compare_papr_methods.py
    PYTHONPATH=src:. python examples/compare_papr_methods.py --blocks 16 --snr 12 --seed 7
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from ofdm_linksim.factory import compare_papr_methods


def main() -> int:
    p = argparse.ArgumentParser(description="Compare OFDM PAPR methods")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--blocks", type=int, default=16)
    p.add_argument("--snr", type=float, default=15.0)
    p.add_argument(
        "--methods",
        nargs="*",
        default=None,
        help="Subset of methods (default: all)",
    )
    args = p.parse_args()

    rows = compare_papr_methods(
        methods=args.methods,
        seed=args.seed,
        n_blocks=args.blocks,
        snr_db=args.snr,
    )

    print("=" * 72)
    print("OFDM-PAPR-LinkSim — method comparison")
    print("=" * 72)
    print(f"  seed={args.seed}  blocks={args.blocks}  SNR={args.snr} dB")
    print("-" * 72)
    print(f"{'method':<20} {'PAPR [dB]':>10} {'BER':>12} {'EVM %':>10}")
    print("-" * 72)
    for r in rows:
        print(
            f"{r['method']:<20} {r['papr_db']:10.3f} {r['ber']:12.3e} "
            f"{r['evm_rms_percent']:10.2f}"
        )
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
