#!/usr/bin/env python3
"""
PAPR parameter sweep
====================

Batch PAPR campaigns over methods, clipping ratios, and block counts.

Stage-1 focus
-------------
- method ``none``  (locked reference)
- method ``clipping`` with a CR grid

For each (method, parameter) point the script:

1. Builds uncoded QPSK-OFDM transmit frames
2. Applies the PAPR method
3. Collects per-block PAPR (dB) on useful samples
4. Computes empirical CCDF + summary statistics
5. Writes JSON / CSV under ``results/``

Usage
-----
    python scripts/run_papr_sweep.py
    python scripts/run_papr_sweep.py --methods none,clipping --blocks 500
    python scripts/run_papr_sweep.py --clip-ratios 1.2,1.5,1.8 --seed 7
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
for p in (_SRC, _REPO):
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

from ofdm_linksim.analysis.ccdf import ccdf_at_probabilities, compute_ccdf
from ofdm_linksim.core.types import (
    CCDF_REPORT_PROBABILITIES,
    DEFAULT_CP_LENGTH,
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERSAMPLING,
    DEFAULT_SEED,
    MappingType,
    ModulationType,
    PAPRMethod,
)
from ofdm_linksim.modulation import bits_per_symbol, modulate
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.papr import get_useful_samples
from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.utils.random import make_stream_rngs
from ofdm_linksim.core.types import make_papr_result, safe_mean_power

from papr_methods.clipping import apply_clipping
from papr_methods.none import apply_none


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

N_DATA = 192
MOD = ModulationType.QPSK


@dataclass
class SweepPointResult:
    method: str
    clipping_ratio: Optional[float]
    seed: int
    n_blocks: int
    fft_size: int
    n_data: int
    oversampling: int
    mean_papr_db: float
    median_papr_db: float
    std_papr_db: float
    min_papr_db: float
    max_papr_db: float
    papr_at_1e1: float
    papr_at_1e2: float
    papr_at_1e3: float
    papr_at_1e4: float
    n_samples_total: int
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> Dict[str, Any]:
        d = asdict(self)
        meta = d.pop("meta", {})
        d["meta_json"] = json.dumps(meta, default=str)
        return d


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OFDM PAPR parameter sweep")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--blocks", type=int, default=200, help="OFDM symbols per point")
    p.add_argument("--fft-size", type=int, default=DEFAULT_FFT_SIZE)
    p.add_argument("--n-data", type=int, default=N_DATA)
    p.add_argument("--cp", type=int, default=DEFAULT_CP_LENGTH)
    p.add_argument("--oversampling", type=int, default=DEFAULT_OVERSAMPLING)
    p.add_argument(
        "--methods",
        type=str,
        default="none,clipping",
        help="Comma-separated: none,clipping",
    )
    p.add_argument(
        "--clip-ratios",
        type=str,
        default="1.2,1.4,1.6,1.8",
        help="Clipping ratios for method=clipping",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("results/experiments/papr_sweep"),
    )
    p.add_argument(
        "--save-raw",
        action="store_true",
        help="Save per-block PAPR arrays as .npz",
    )
    return p.parse_args()


def _parse_float_list(text: str) -> List[float]:
    parts = [x.strip() for x in text.split(",") if x.strip()]
    return [float(x) for x in parts]


def _parse_methods(text: str) -> List[str]:
    allowed = {"none", "clipping"}
    methods = [x.strip().lower() for x in text.split(",") if x.strip()]
    bad = [m for m in methods if m not in allowed]
    if bad:
        raise SystemExit(
            f"Unsupported methods in Stage-1: {bad}. Allowed: {sorted(allowed)}"
        )
    if not methods:
        raise SystemExit("At least one method is required.")
    return methods


# ---------------------------------------------------------------------------
# TX + per-block PAPR
# ---------------------------------------------------------------------------

def build_transmit_frame(
    *,
    seed: int,
    n_blocks: int,
    fft_size: int,
    n_data: int,
    cp_length: int,
    oversampling: int,
):
    streams = make_stream_rngs(seed)
    bps = bits_per_symbol(MOD)
    n_bits = n_data * n_blocks * bps
    bits = generate_random_bits(n_bits, rng=streams["source"])
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
    return tx, streams


def useful_per_symbol(tx) -> np.ndarray:
    """Return useful samples shaped (n_symbols, samples_per_symbol)."""
    useful = np.asarray(get_useful_samples(tx.waveform), dtype=np.complex128)
    n_sym = int(tx.waveform.n_symbols)
    if useful.ndim == 2:
        return useful
    if useful.size % n_sym != 0:
        raise ValueError("Useful sample count is not divisible by n_symbols.")
    return useful.reshape(n_sym, -1)


def per_block_papr_db_from_useful(useful_2d: np.ndarray) -> np.ndarray:
    vals = []
    for row in useful_2d:
        pr = make_papr_result(row.ravel(), cp_excluded=True)
        vals.append(pr.papr_db)
    return np.asarray(vals, dtype=np.float64)


def apply_method_to_useful(
    useful_2d: np.ndarray,
    *,
    method: str,
    clipping_ratio: Optional[float],
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Return possibly modified useful grid + meta.

    For ``none``: identity.
    For ``clipping``: hard clip using RMS of the whole useful grid.
    """
    meta: Dict[str, Any] = {"method": method}
    if method == "none":
        meta["modified"] = False
        return useful_2d.copy(), meta

    if method == "clipping":
        if clipping_ratio is None or clipping_ratio <= 0:
            raise ValueError("clipping_ratio must be positive.")
        flat = useful_2d.ravel()
        p_avg = safe_mean_power(flat)
        rms = float(np.sqrt(p_avg))
        amp = float(clipping_ratio * rms)
        mag = np.abs(flat)
        scale = np.ones_like(mag, dtype=np.float64)
        mask = mag > amp
        scale[mask] = amp / mag[mask]
        clipped = (flat * scale).astype(np.complex128).reshape(useful_2d.shape)
        meta.update(
            {
                "modified": True,
                "clipping_ratio": float(clipping_ratio),
                "amplitude": amp,
                "rms": rms,
                "mode": "hard",
            }
        )
        return clipped, meta

    raise ValueError(f"Unknown method: {method}")


def quantiles_at_probs(papr_db: np.ndarray, probs: Sequence[float]) -> Dict[float, float]:
    """
    Empirical PAPR threshold γ such that CCDF(γ) ≈ p
    i.e. fraction of blocks with PAPR > γ equals p.
    """
    try:
        return dict(zip(probs, ccdf_at_probabilities(papr_db, probabilities=probs)))
    except Exception:
        # fallback: percentile of the upper tail
        out = {}
        for p in probs:
            out[p] = float(np.quantile(papr_db, 1.0 - p))
        return out


def run_point(
    *,
    method: str,
    clipping_ratio: Optional[float],
    seed: int,
    n_blocks: int,
    fft_size: int,
    n_data: int,
    cp_length: int,
    oversampling: int,
) -> Tuple[SweepPointResult, np.ndarray]:
    tx, _streams = build_transmit_frame(
        seed=seed,
        n_blocks=n_blocks,
        fft_size=fft_size,
        n_data=n_data,
        cp_length=cp_length,
        oversampling=oversampling,
    )
    useful = useful_per_symbol(tx)
    processed, meta = apply_method_to_useful(
        useful, method=method, clipping_ratio=clipping_ratio
    )
    papr_db = per_block_papr_db_from_useful(processed)
    q = quantiles_at_probs(papr_db, CCDF_REPORT_PROBABILITIES)

    point = SweepPointResult(
        method=method,
        clipping_ratio=clipping_ratio,
        seed=seed,
        n_blocks=n_blocks,
        fft_size=fft_size,
        n_data=n_data,
        oversampling=oversampling,
        mean_papr_db=float(np.mean(papr_db)),
        median_papr_db=float(np.median(papr_db)),
        std_papr_db=float(np.std(papr_db)),
        min_papr_db=float(np.min(papr_db)),
        max_papr_db=float(np.max(papr_db)),
        papr_at_1e1=float(q.get(1e-1, float("nan"))),
        papr_at_1e2=float(q.get(1e-2, float("nan"))),
        papr_at_1e3=float(q.get(1e-3, float("nan"))),
        papr_at_1e4=float(q.get(1e-4, float("nan"))),
        n_samples_total=int(processed.size),
        meta=meta,
    )
    return point, papr_db


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    if not rows:
        return
    keys: List[str] = []
    seen = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_json(data: Any, path: Path) -> None:
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    methods = _parse_methods(args.methods)
    clip_ratios = _parse_float_list(args.clip_ratios)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_root = ensure_dir(args.output / f"sweep_seed{args.seed}_{stamp}")

    jobs: List[Tuple[str, Optional[float]]] = []
    for m in methods:
        if m == "none":
            jobs.append(("none", None))
        else:
            for cr in clip_ratios:
                jobs.append(("clipping", cr))

    print("=" * 72)
    print("OFDM-PAPR-LinkSim — PAPR sweep")
    print("=" * 72)
    print(f"  seed        : {args.seed}")
    print(f"  blocks      : {args.blocks}")
    print(f"  methods     : {methods}")
    print(f"  clip ratios : {clip_ratios if 'clipping' in methods else 'n/a'}")
    print(f"  output      : {out_root}")
    print("-" * 72)

    rows: List[Dict[str, Any]] = []
    raw_dir = ensure_dir(out_root / "raw_papr") if args.save_raw else None

    for method, cr in jobs:
        label = method if cr is None else f"{method}_CR{cr:g}"
        print(f"  → {label} ...", flush=True)
        point, papr_db = run_point(
            method=method,
            clipping_ratio=cr,
            seed=args.seed,
            n_blocks=args.blocks,
            fft_size=args.fft_size,
            n_data=args.n_data,
            cp_length=args.cp,
            oversampling=args.oversampling,
        )
        rows.append(point.to_row())

        # CCDF curve for this point
        ccdf = compute_ccdf(papr_db)
        ccdf_path = out_root / f"ccdf_{label}.json"
        write_json(
            {
                "label": label,
                "method": method,
                "clipping_ratio": cr,
                "n_blocks": int(papr_db.size),
                "thresholds_db": ccdf.thresholds_db.tolist(),
                "probabilities": ccdf.probabilities.tolist(),
                "summary": point.to_row(),
            },
            ccdf_path,
        )

        if raw_dir is not None:
            np.savez_compressed(
                raw_dir / f"papr_db_{label}.npz",
                papr_db=papr_db,
            )

        print(
            f"     mean={point.mean_papr_db:.3f} dB  "
            f"max={point.max_papr_db:.3f} dB  "
            f"@1e-3={point.papr_at_1e3:.3f} dB"
        )

    write_csv(rows, out_root / "sweep_summary.csv")
    write_json(
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "seed": args.seed,
            "blocks": args.blocks,
            "methods": methods,
            "clip_ratios": clip_ratios,
            "points": rows,
        },
        out_root / "sweep_summary.json",
    )

    print("-" * 72)
    print(f"  wrote {len(rows)} points → {out_root}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
