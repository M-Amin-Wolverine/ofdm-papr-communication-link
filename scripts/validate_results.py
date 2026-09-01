#!/usr/bin/env python3
"""
Validate experiment result directories
====================================

Checks structural and scientific invariants for runs produced by
``ResultWriter``, ``run_baseline.py``, or ``run_papr_sweep.py``.

Examples
--------
    python scripts/validate_results.py results/baseline
    python scripts/validate_results.py results/experiments/papr_sweep --recursive
    python scripts/validate_results.py path/to/one_run_dir --strict
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Report model
# ---------------------------------------------------------------------------

@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class DirReport:
    path: str
    kind: str
    checks: List[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append(Check(name=name, ok=ok, detail=detail))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_finite_number(x: Any) -> bool:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v)


def find_candidate_dirs(root: Path, *, recursive: bool) -> List[Path]:
    """
    A candidate run dir contains at least one known artifact.
    """
    markers = (
        "experiment_result.json",
        "summary.json",
        "sweep_summary.json",
        "write_manifest.json",
        "papr",
        "ber",
        "metadata",
    )
    if not root.exists():
        return []

    if any((root / m).exists() for m in markers):
        bases = [root]
    else:
        bases = []

    if recursive or not bases:
        for p in sorted(root.rglob("*")):
            if not p.is_dir():
                continue
            if any((p / m).exists() for m in markers):
                bases.append(p)

    # unique, preserve order
    seen = set()
    out: List[Path] = []
    for p in bases:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


def classify_dir(path: Path) -> str:
    if (path / "sweep_summary.json").exists() or (path / "sweep_summary.csv").exists():
        return "papr_sweep"
    if (path / "experiment_result.json").exists() or (path / "summary.json").exists():
        return "experiment_run"
    if (path / "write_manifest.json").exists():
        return "experiment_run"
    return "unknown"


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_papr_dict(d: Dict[str, Any], report: DirReport, *, prefix: str = "papr") -> None:
    required = ("papr_linear", "papr_db")
    for k in required:
        if k not in d:
            report.add(f"{prefix}.{k}.present", False, f"missing key {k}")
            return

    lin = d.get("papr_linear")
    db = d.get("papr_db")
    report.add(f"{prefix}.papr_linear.finite", is_finite_number(lin), str(lin))
    report.add(f"{prefix}.papr_db.finite", is_finite_number(db), str(db))

    if is_finite_number(lin):
        report.add(f"{prefix}.papr_linear.ge_1", float(lin) >= 1.0 - 1e-9, str(lin))
        if is_finite_number(db):
            expected = 10.0 * math.log10(float(lin))
            ok = abs(float(db) - expected) <= 1e-3 + 1e-6 * abs(expected)
            report.add(
                f"{prefix}.db_matches_linear",
                ok,
                f"db={db}, expected={expected:.6f}",
            )

    if "n_samples_used" in d:
        n = d["n_samples_used"]
        report.add(
            f"{prefix}.n_samples_used.positive",
            isinstance(n, int) and n > 0,
            str(n),
        )
    if "cp_excluded" in d:
        report.add(
            f"{prefix}.cp_excluded",
            d["cp_excluded"] is True,
            str(d["cp_excluded"]),
        )
    if "peak_power" in d and "average_power" in d:
        if is_finite_number(d["peak_power"]) and is_finite_number(d["average_power"]):
            report.add(
                f"{prefix}.peak_ge_avg",
                float(d["peak_power"]) >= float(d["average_power"]) - 1e-12,
                f"peak={d['peak_power']}, avg={d['average_power']}",
            )


def validate_ber_dict(d: Dict[str, Any], report: DirReport, *, prefix: str = "ber") -> None:
    for k in ("bit_errors", "total_bits", "ber"):
        if k not in d:
            report.add(f"{prefix}.{k}.present", False, "missing")
            return
    be, tb, ber = d["bit_errors"], d["total_bits"], d["ber"]
    report.add(f"{prefix}.total_bits.positive", isinstance(tb, int) and tb > 0, str(tb))
    report.add(
        f"{prefix}.bit_errors.range",
        isinstance(be, int) and 0 <= be <= tb,
        str(be),
    )
    if is_finite_number(ber):
        report.add(f"{prefix}.ber.range", 0.0 <= float(ber) <= 1.0, str(ber))
        if isinstance(be, int) and isinstance(tb, int) and tb > 0:
            expected = be / tb
            report.add(
                f"{prefix}.ber.consistent",
                abs(float(ber) - expected) <= 1e-9 + 1e-12,
                f"ber={ber}, expected={expected}",
            )


def validate_experiment_run(path: Path, report: DirReport, *, strict: bool) -> None:
    summary = path / "summary.json"
    full = path / "experiment_result.json"
    manifest = path / "write_manifest.json"

    report.add("summary.json.present", summary.exists() or full.exists(), "")
    if summary.exists():
        try:
            data = load_json(summary)
            report.add("summary.json.parse", True, "")
            if isinstance(data, dict):
                if "papr_db" in data and is_finite_number(data["papr_db"]):
                    report.add("summary.papr_db.finite", True, str(data["papr_db"]))
                if "ber" in data and data["ber"] is not None:
                    report.add(
                        "summary.ber.range",
                        is_finite_number(data["ber"]) and 0 <= float(data["ber"]) <= 1,
                        str(data["ber"]),
                    )
        except Exception as exc:
            report.add("summary.json.parse", False, str(exc))

    if full.exists():
        try:
            data = load_json(full)
            report.add("experiment_result.json.parse", True, "")
            if isinstance(data, dict):
                if "papr" in data and isinstance(data["papr"], dict):
                    validate_papr_dict(data["papr"], report, prefix="experiment.papr")
                if "ber" in data and isinstance(data["ber"], dict):
                    validate_ber_dict(data["ber"], report, prefix="experiment.ber")
                if "metadata" in data and isinstance(data["metadata"], dict):
                    md = data["metadata"]
                    report.add(
                        "metadata.seed.present",
                        "seed" in md,
                        str(md.get("seed")),
                    )
        except Exception as exc:
            report.add("experiment_result.json.parse", False, str(exc))

    papr_json = path / "papr" / "papr.json"
    if papr_json.exists():
        try:
            validate_papr_dict(load_json(papr_json), report, prefix="file.papr")
        except Exception as exc:
            report.add("file.papr.parse", False, str(exc))
    elif strict:
        report.add("file.papr.present", False, "papr/papr.json missing (strict)")

    ber_json = path / "ber" / "ber.json"
    if ber_json.exists():
        try:
            validate_ber_dict(load_json(ber_json), report, prefix="file.ber")
        except Exception as exc:
            report.add("file.ber.parse", False, str(exc))

    if manifest.exists():
        try:
            man = load_json(manifest)
            report.add("manifest.parse", True, "")
            if isinstance(man, dict) and "ok" in man:
                report.add("manifest.ok", bool(man["ok"]), str(man.get("ok")))
        except Exception as exc:
            report.add("manifest.parse", False, str(exc))


def validate_papr_sweep(path: Path, report: DirReport, *, strict: bool) -> None:
    summary = path / "sweep_summary.json"
    csv_path = path / "sweep_summary.csv"
    report.add("sweep_summary.present", summary.exists() or csv_path.exists(), "")

    if not summary.exists():
        if strict:
            report.add("sweep_summary.json.required", False, "missing")
        return

    try:
        data = load_json(summary)
        report.add("sweep_summary.parse", True, "")
    except Exception as exc:
        report.add("sweep_summary.parse", False, str(exc))
        return

    points = data.get("points") if isinstance(data, dict) else None
    if not isinstance(points, list) or not points:
        report.add("sweep_summary.points", False, "empty or missing")
        return

    report.add("sweep_summary.points", True, f"n={len(points)}")
    for i, pt in enumerate(points):
        if not isinstance(pt, dict):
            report.add(f"point[{i}].type", False, "not a dict")
            continue
        for key in ("method", "mean_papr_db", "max_papr_db", "n_blocks"):
            report.add(
                f"point[{i}].{key}.present",
                key in pt,
                str(pt.get(key)),
            )
        if is_finite_number(pt.get("mean_papr_db")):
            report.add(
                f"point[{i}].mean_papr_db.ge_0",
                float(pt["mean_papr_db"]) >= 0.0,
                str(pt["mean_papr_db"]),
            )
        method = str(pt.get("method", "")).lower()
        if method not in {"none", "clipping"}:
            report.add(
                f"point[{i}].method.stage1",
                False,
                f"unexpected method {method!r} in Stage-1 validator",
            )
        else:
            report.add(f"point[{i}].method.stage1", True, method)

    # CCDF sidecars optional but checked if present
    for ccdf_file in sorted(path.glob("ccdf_*.json")):
        try:
            ccdf = load_json(ccdf_file)
            thr = ccdf.get("thresholds_db", [])
            pr = ccdf.get("probabilities", [])
            ok = (
                isinstance(thr, list)
                and isinstance(pr, list)
                and len(thr) == len(pr)
                and len(thr) > 0
            )
            report.add(f"ccdf.{ccdf_file.name}.shape", ok, f"n={len(thr)}")
            if ok and pr:
                report.add(
                    f"ccdf.{ccdf_file.name}.prob_range",
                    all(is_finite_number(x) and 0.0 <= float(x) <= 1.0 for x in pr),
                    "",
                )
        except Exception as exc:
            report.add(f"ccdf.{ccdf_file.name}.parse", False, str(exc))


def validate_dir(path: Path, *, strict: bool) -> DirReport:
    kind = classify_dir(path)
    report = DirReport(path=str(path), kind=kind)
    report.add("directory.exists", path.is_dir(), str(path))

    if kind == "papr_sweep":
        validate_papr_sweep(path, report, strict=strict)
    elif kind == "experiment_run":
        validate_experiment_run(path, report, strict=strict)
    else:
        report.add(
            "recognized_layout",
            False,
            "no experiment_result/summary/sweep_summary markers found",
        )
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate OFDM-PAPR-LinkSim result directories")
    p.add_argument(
        "path",
        type=Path,
        help="Run directory or parent folder (e.g. results/baseline)",
    )
    p.add_argument(
        "--recursive",
        action="store_true",
        help="Discover run dirs under the given path",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Require optional artifacts (papr/ber files, etc.)",
    )
    p.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write machine-readable report JSON",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = args.path
    if not root.exists():
        print(f"[validate] path does not exist: {root}", file=sys.stderr)
        return 2

    dirs = find_candidate_dirs(root, recursive=args.recursive)
    if not dirs:
        # validate the path itself anyway
        dirs = [root]

    reports = [validate_dir(d, strict=args.strict) for d in dirs]

    print("=" * 72)
    print("OFDM-PAPR-LinkSim — result validation")
    print("=" * 72)
    print(f"  root      : {root}")
    print(f"  runs found: {len(reports)}")
    print(f"  strict    : {args.strict}")
    print("-" * 72)

    n_fail = 0
    for rep in reports:
        status = "OK" if rep.ok else "FAIL"
        if not rep.ok:
            n_fail += 1
        print(f"[{status}] ({rep.kind}) {rep.path}")
        for c in rep.checks:
            mark = "✓" if c.ok else "✗"
            extra = f" — {c.detail}" if c.detail and not c.ok else ""
            if not c.ok or args.strict:
                print(f"    {mark} {c.name}{extra}")
        # always show failures; in non-strict only print failed checks above
        failed = [c for c in rep.checks if not c.ok]
        if failed and not args.strict:
            pass  # already printed
        elif rep.ok:
            print(f"    ✓ {len(rep.checks)} checks passed")

    print("-" * 72)
    print(f"  failed runs: {n_fail}/{len(reports)}")
    print("=" * 72)

    if args.json_out is not None:
        payload = {
            "root": str(root),
            "strict": args.strict,
            "reports": [
                {
                    "path": r.path,
                    "kind": r.kind,
                    "ok": r.ok,
                    "checks": [c.__dict__ for c in r.checks],
                }
                for r in reports
            ],
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"  report JSON → {args.json_out}")

    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
