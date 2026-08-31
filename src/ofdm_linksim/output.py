"""
Result persistence and export for OFDM-PAPR-LinkSim
===================================================

Writes experiment artefacts to disk in a reproducible, research-friendly
layout that mirrors ``configs/baseline.yaml`` → ``results.*`` sections.

Supported artefacts
-------------------
- JSON metadata and full ``ExperimentResult`` dumps
- CSV tables (BER vs SNR, PAPR CCDF, summary rows)
- NumPy ``.npz`` archives for arrays (CCDF, PSD, constellation, …)
- Optional human-readable summary ``.txt``
- Configuration sidecar (JSON) next to every run

Design rules
------------
1. Never overwrite existing run directories unless ``overwrite=True``.
2. Every write is accompanied by a metadata record (seed, fingerprint, time).
3. Directory layout follows ``ResultsSection`` from ``config.py``.
4. No global mutable state; ``ResultWriter`` is instantiated per experiment.
5. Missing optional metrics (e.g. no EVM) are skipped cleanly.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np

from ofdm_linksim.core.types import (
    BERResult,
    CCDFResult,
    ConstellationSnapshot,
    EVMResult,
    ExperimentResult,
    PAPRResult,
    PAPRStatistics,
    PSDResult,
    SimulationMetadata,
)

# Optional config dependency (loaded lazily-friendly)
try:
    from ofdm_linksim.config import ExperimentConfig, ResultsSection
except ImportError:  # pragma: no cover
    ExperimentConfig = Any  # type: ignore
    ResultsSection = Any  # type: ignore


PathLike = Union[str, os.PathLike]


# =============================================================================
# Path / naming helpers
# =============================================================================

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp_for_dirname() -> str:
    """Filesystem-safe UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: PathLike, *, exist_ok: bool = True) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=exist_ok)
    return p


def safe_name(text: str, *, max_len: int = 80) -> str:
    """Turn an arbitrary string into a conservative directory / file token."""
    allowed = []
    for ch in str(text):
        if ch.isalnum() or ch in ("-", "_", "."):
            allowed.append(ch)
        elif ch in (" ", "/", "\\", ":"):
            allowed.append("_")
    token = "".join(allowed).strip("._")
    if not token:
        token = "run"
    return token[:max_len]


def run_directory_name(
    *,
    scenario_name: str,
    run_id: str,
    seed: int,
    stamp: Optional[str] = None,
) -> str:
    ts = stamp or utc_stamp_for_dirname()
    return (
        f"{safe_name(scenario_name)}"
        f"__seed{int(seed)}"
        f"__{safe_name(run_id)}"
        f"__{ts}"
    )


# =============================================================================
# Serialization helpers
# =============================================================================

def _json_default(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "value"):  # Enum
        try:
            return obj.value
        except Exception:
            pass
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def write_json(data: Any, path: PathLike, *, indent: int = 2) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    text = json.dumps(data, indent=indent, default=_json_default, ensure_ascii=False)
    p.write_text(text + "\n", encoding="utf-8")
    return p


def read_json(path: PathLike) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(text: str, path: PathLike) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    p.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
    return p


def write_csv_rows(
    rows: Sequence[Mapping[str, Any]],
    path: PathLike,
    *,
    fieldnames: Optional[Sequence[str]] = None,
) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    if not rows:
        # still create an empty file with header if fieldnames given
        with p.open("w", encoding="utf-8", newline="") as fh:
            if fieldnames:
                writer = csv.DictWriter(fh, fieldnames=list(fieldnames))
                writer.writeheader()
        return p

    keys: List[str]
    if fieldnames is not None:
        keys = list(fieldnames)
    else:
        keys = []
        seen = set()
        for row in rows:
            for k in row.keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)

    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            flat = {k: _csv_cell(row.get(k)) for k in keys}
            writer.writerow(flat)
    return p


def _csv_cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return json.dumps(value.tolist())
    return value


def write_npz(path: PathLike, **arrays: Any) -> Path:
    """Save a dictionary of arrays; non-array values are ignored with a warning."""
    p = Path(path)
    ensure_dir(p.parent)
    clean: Dict[str, np.ndarray] = {}
    for key, val in arrays.items():
        if val is None:
            continue
        if isinstance(val, np.ndarray):
            clean[key] = val
        elif isinstance(val, (list, tuple)):
            clean[key] = np.asarray(val)
        elif isinstance(val, (int, float, bool, np.number)):
            clean[key] = np.asarray(val)
        else:
            warnings.warn(
                f"Skipping non-array key '{key}' of type {type(val)} in NPZ.",
                UserWarning,
                stacklevel=2,
            )
    np.savez_compressed(str(p), **clean)
    return p


# =============================================================================
# Metric → table converters
# =============================================================================

def ber_to_row(ber: BERResult) -> Dict[str, Any]:
    return {
        "bit_errors": ber.bit_errors,
        "total_bits": ber.total_bits,
        "ber": ber.ber,
        "snr_db": ber.snr_db,
    }


def evm_to_row(evm: EVMResult) -> Dict[str, Any]:
    return {
        "rms_evm": evm.rms_evm,
        "rms_evm_percent": evm.rms_evm_percent,
        "peak_evm": evm.peak_evm,
        "peak_evm_percent": evm.peak_evm_percent,
    }


def papr_to_row(papr: PAPRResult) -> Dict[str, Any]:
    return {
        "papr_linear": papr.papr_linear,
        "papr_db": papr.papr_db,
        "peak_power": papr.peak_power,
        "average_power": papr.average_power,
        "peak_index": papr.peak_index,
        "cp_excluded": papr.cp_excluded,
        "n_samples_used": papr.n_samples_used,
    }


def papr_statistics_to_row(stats: PAPRStatistics) -> Dict[str, Any]:
    d = {
        "mean_papr_db": stats.mean_papr_db,
        "median_papr_db": stats.median_papr_db,
        "std_papr_db": stats.std_papr_db,
        "min_papr_db": stats.min_papr_db,
        "max_papr_db": stats.max_papr_db,
        "n_blocks": stats.n_blocks,
        "papr_at_1e1": stats.papr_at_1e1,
        "papr_at_1e2": stats.papr_at_1e2,
        "papr_at_1e3": stats.papr_at_1e3,
        "papr_at_1e4": stats.papr_at_1e4,
    }
    return d


def ccdf_to_rows(ccdf: CCDFResult) -> List[Dict[str, Any]]:
    thr = np.asarray(ccdf.thresholds_db, dtype=np.float64).ravel()
    pr = np.asarray(ccdf.probabilities, dtype=np.float64).ravel()
    rows = []
    for t, p in zip(thr, pr):
        rows.append(
            {
                "threshold_db": float(t),
                "probability": float(p),
                "n_blocks": int(ccdf.n_blocks),
                "method": ccdf.method,
            }
        )
    return rows


def psd_to_rows(psd: PSDResult) -> List[Dict[str, Any]]:
    f = np.asarray(psd.frequencies, dtype=np.float64).ravel()
    p = np.asarray(psd.psd_db, dtype=np.float64).ravel()
    rows = []
    for fi, pi in zip(f, p):
        rows.append(
            {
                "frequency_hz": float(fi),
                "psd_db": float(pi),
                "method": psd.method,
                "nperseg": int(psd.nperseg),
                "noverlap": int(psd.noverlap),
                "window": psd.window,
            }
        )
    return rows


def experiment_summary_row(result: ExperimentResult) -> Dict[str, Any]:
    base = result.summary()
    base["created_at"] = result.metadata.created_at
    base["notes"] = result.notes
    return base


# =============================================================================
# Human-readable summary
# =============================================================================

def format_text_summary(result: ExperimentResult) -> str:
    lines: List[str] = []
    md = result.metadata
    lines.append("=" * 72)
    lines.append("OFDM-PAPR-LinkSim — Experiment Summary")
    lines.append("=" * 72)
    lines.append(f"Run ID          : {md.run_id}")
    lines.append(f"Scenario        : {md.scenario_name} v{md.scenario_version}")
    lines.append(f"Created (UTC)   : {md.created_at}")
    lines.append(f"Seed            : {md.seed}")
    lines.append(f"Modulation      : {md.modulation.value}")
    lines.append(f"Channel         : {md.channel.value}")
    lines.append(f"PAPR method     : {md.papr_method.value}")
    lines.append(f"FFT size        : {md.fft_size}")
    lines.append(f"Oversampling    : {md.oversampling}")
    lines.append(f"OFDM symbols    : {md.n_ofdm_symbols}")
    lines.append(f"SNR definition  : {md.snr_definition.value}")
    lines.append("-" * 72)

    if result.papr is not None:
        lines.append(
            f"PAPR            : {result.papr.papr_db:.4f} dB "
            f"(linear={result.papr.papr_linear:.6f}, "
            f"samples={result.papr.n_samples_used})"
        )
    if result.papr_statistics is not None:
        st = result.papr_statistics
        lines.append(
            f"PAPR stats      : mean={st.mean_papr_db:.4f} dB, "
            f"median={st.median_papr_db:.4f} dB, "
            f"max={st.max_papr_db:.4f} dB, n_blocks={st.n_blocks}"
        )
        lines.append(
            f"PAPR @ CCDF     : "
            f"1e-1={st.papr_at_1e1:.4f}, "
            f"1e-2={st.papr_at_1e2:.4f}, "
            f"1e-3={st.papr_at_1e3:.4f}, "
            f"1e-4={st.papr_at_1e4:.4f} dB"
        )
    if result.ber is not None:
        lines.append(
            f"BER             : {result.ber.ber:.6e} "
            f"({result.ber.bit_errors}/{result.ber.total_bits})"
            + (
                f" @ SNR={result.ber.snr_db} dB"
                if result.ber.snr_db is not None
                else ""
            )
        )
    if result.evm is not None:
        lines.append(
            f"EVM             : RMS={result.evm.rms_evm_percent:.4f} %, "
            f"Peak={result.evm.peak_evm_percent:.4f} %"
        )
    if result.ccdf is not None:
        lines.append(
            f"CCDF            : {len(result.ccdf.thresholds_db)} points, "
            f"method={result.ccdf.method}, n_blocks={result.ccdf.n_blocks}"
        )
    if result.psd is not None:
        lines.append(
            f"PSD             : method={result.psd.method}, "
            f"nperseg={result.psd.nperseg}, bins={len(result.psd.frequencies)}"
        )
    if result.notes:
        lines.append("-" * 72)
        lines.append("Notes:")
        lines.append(result.notes)
    lines.append("=" * 72)
    return "\n".join(lines)


# =============================================================================
# ResultWriter
# =============================================================================

@dataclass
class WriteReport:
    """Manifest of everything written for one experiment."""

    root: str
    run_dir: str
    files: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""
    ok: bool = True
    errors: List[str] = field(default_factory=list)

    def add(self, path: PathLike) -> None:
        self.files.append(str(path))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": self.root,
            "run_dir": self.run_dir,
            "files": list(self.files),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "ok": self.ok,
            "errors": list(self.errors),
        }


@dataclass
class ResultWriter:
    """
    High-level writer bound to a results root directory.

    Typical usage
    -------------
    >>> writer = ResultWriter.from_config(cfg)
    >>> report = writer.write_experiment(result)
    """

    root: Path
    overwrite: bool = False
    save_raw_data: bool = True
    save_processed_data: bool = True
    save_configuration: bool = True
    save_metadata: bool = True
    save_summary: bool = True
    enable_csv: bool = True
    enable_json: bool = True
    enable_numpy: bool = True
    # optional sub-dir names (relative to root or absolute)
    dir_papr: str = "papr"
    dir_ber: str = "ber"
    dir_evm: str = "evm"
    dir_psd: str = "psd"
    dir_figures: str = "figures"
    dir_metadata: str = "metadata"

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_results_section(
        cls,
        section: Any,
        *,
        root_override: Optional[PathLike] = None,
    ) -> "ResultWriter":
        root = Path(root_override or getattr(section, "root_directory", "results/baseline"))
        return cls(
            root=root,
            overwrite=bool(getattr(section, "overwrite", False)),
            save_raw_data=bool(getattr(section, "save_raw_data", True)),
            save_processed_data=bool(getattr(section, "save_processed_data", True)),
            save_configuration=bool(getattr(section, "save_configuration", True)),
            save_metadata=bool(getattr(section, "save_metadata", True)),
            save_summary=bool(getattr(section, "save_summary", True)),
            enable_csv=bool(getattr(section, "csv", True)),
            enable_json=bool(getattr(section, "json", True)),
            enable_numpy=bool(getattr(section, "numpy", True)),
            dir_papr=str(getattr(section, "dir_papr", "papr")),
            dir_ber=str(getattr(section, "dir_ber", "ber")),
            dir_evm=str(getattr(section, "dir_evm", "evm")),
            dir_psd=str(getattr(section, "dir_psd", "psd")),
            dir_figures=str(getattr(section, "dir_figures", "figures")),
            dir_metadata=str(getattr(section, "dir_metadata", "metadata")),
        )

    @classmethod
    def from_config(
        cls,
        cfg: Any,
        *,
        root_override: Optional[PathLike] = None,
    ) -> "ResultWriter":
        section = getattr(cfg, "results", None)
        if section is None:
            return cls(root=Path(root_override or "results/baseline"))
        return cls.from_results_section(section, root_override=root_override)

    # ------------------------------------------------------------------
    # Directory layout
    # ------------------------------------------------------------------
    def prepare_run_dir(
        self,
        result: ExperimentResult,
        *,
        stamp: Optional[str] = None,
    ) -> Path:
        name = run_directory_name(
            scenario_name=result.metadata.scenario_name,
            run_id=result.metadata.run_id,
            seed=result.metadata.seed,
            stamp=stamp,
        )
        run_dir = self.root / name
        if run_dir.exists():
            if not self.overwrite:
                raise FileExistsError(
                    f"Run directory already exists: {run_dir}. "
                    "Set overwrite=True to replace."
                )
            shutil.rmtree(run_dir)
        ensure_dir(run_dir)
        # standard subfolders
        for sub in (
            self.dir_papr,
            self.dir_ber,
            self.dir_evm,
            self.dir_psd,
            self.dir_figures,
            self.dir_metadata,
        ):
            # if absolute path configured, still create under run_dir with basename
            sub_name = Path(sub).name
            ensure_dir(run_dir / sub_name)
        return run_dir

    # ------------------------------------------------------------------
    # Core write API
    # ------------------------------------------------------------------
    def write_experiment(
        self,
        result: ExperimentResult,
        *,
        config: Optional[Any] = None,
        extra_files: Optional[Mapping[str, Any]] = None,
        stamp: Optional[str] = None,
    ) -> WriteReport:
        """
        Persist a full ``ExperimentResult``.

        Returns a ``WriteReport`` listing every written path.
        """
        if not isinstance(result, ExperimentResult):
            raise TypeError("result must be an ExperimentResult instance.")

        run_dir = self.prepare_run_dir(result, stamp=stamp)
        report = WriteReport(root=str(self.root), run_dir=str(run_dir))
        t0 = time.perf_counter()

        try:
            # --- full JSON dump ---
            if self.enable_json and self.save_processed_data:
                path = write_json(
                    result.to_dict(),
                    run_dir / "experiment_result.json",
                )
                report.add(path)

            # --- summary ---
            if self.save_summary:
                summary = experiment_summary_row(result)
                if self.enable_json:
                    path = write_json(summary, run_dir / "summary.json")
                    report.add(path)
                if self.enable_csv:
                    path = write_csv_rows([summary], run_dir / "summary.csv")
                    report.add(path)
                path = write_text(
                    format_text_summary(result),
                    run_dir / "summary.txt",
                )
                report.add(path)

            # --- metadata ---
            if self.save_metadata and self.enable_json:
                path = write_json(
                    result.metadata.to_dict(),
                    run_dir / Path(self.dir_metadata).name / "metadata.json",
                )
                report.add(path)

            # --- configuration sidecar ---
            if self.save_configuration and config is not None:
                self._write_config(config, run_dir, report)

            # --- per-metric artefacts ---
            self._write_papr(result, run_dir, report)
            self._write_ber(result, run_dir, report)
            self._write_evm(result, run_dir, report)
            self._write_psd(result, run_dir, report)
            self._write_constellation(result, run_dir, report)

            # --- optional caller extras ---
            if extra_files:
                extra_dir = ensure_dir(run_dir / "extra")
                for name, payload in extra_files.items():
                    safe = safe_name(name)
                    if isinstance(payload, (dict, list)):
                        path = write_json(payload, extra_dir / f"{safe}.json")
                    elif isinstance(payload, np.ndarray):
                        path = write_npz(extra_dir / f"{safe}.npz", data=payload)
                    else:
                        path = write_text(str(payload), extra_dir / f"{safe}.txt")
                    report.add(path)

            # --- manifest ---
            report.finished_at = utc_now_iso()
            report.ok = True
            manifest_path = write_json(
                {
                    **report.to_dict(),
                    "elapsed_seconds": time.perf_counter() - t0,
                    "experiment_run_id": result.metadata.run_id,
                },
                run_dir / "write_manifest.json",
            )
            report.add(manifest_path)

        except Exception as exc:
            report.ok = False
            report.errors.append(str(exc))
            report.finished_at = utc_now_iso()
            try:
                write_json(report.to_dict(), run_dir / "write_manifest_ERROR.json")
            except Exception:
                pass
            raise

        return report

    # ------------------------------------------------------------------
    # Metric-specific writers
    # ------------------------------------------------------------------
    def _write_config(
        self,
        config: Any,
        run_dir: Path,
        report: WriteReport,
    ) -> None:
        meta_dir = run_dir / Path(self.dir_metadata).name
        ensure_dir(meta_dir)
        if hasattr(config, "to_plain_dict"):
            data = config.to_plain_dict(include_raw=False)
        elif hasattr(config, "to_dict"):
            data = config.to_dict()
        elif isinstance(config, Mapping):
            data = dict(config)
        else:
            data = {"repr": repr(config)}
        if self.enable_json:
            path = write_json(data, meta_dir / "config.json")
            report.add(path)

    def _write_papr(
        self,
        result: ExperimentResult,
        run_dir: Path,
        report: WriteReport,
    ) -> None:
        sub = run_dir / Path(self.dir_papr).name
        ensure_dir(sub)

        if result.papr is not None:
            row = papr_to_row(result.papr)
            if self.enable_json:
                report.add(write_json(row, sub / "papr.json"))
            if self.enable_csv:
                report.add(write_csv_rows([row], sub / "papr.csv"))

        if result.papr_statistics is not None:
            row = papr_statistics_to_row(result.papr_statistics)
            if self.enable_json:
                report.add(write_json(row, sub / "papr_statistics.json"))
            if self.enable_csv:
                report.add(write_csv_rows([row], sub / "papr_statistics.csv"))

        if result.ccdf is not None:
            rows = ccdf_to_rows(result.ccdf)
            if self.enable_json:
                report.add(
                    write_json(
                        result.ccdf.to_dict(),
                        sub / "ccdf.json",
                    )
                )
            if self.enable_csv:
                report.add(write_csv_rows(rows, sub / "ccdf.csv"))
            if self.enable_numpy and self.save_raw_data:
                report.add(
                    write_npz(
                        sub / "ccdf.npz",
                        thresholds_db=np.asarray(result.ccdf.thresholds_db),
                        probabilities=np.asarray(result.ccdf.probabilities),
                        n_blocks=np.asarray(result.ccdf.n_blocks),
                    )
                )

    def _write_ber(
        self,
        result: ExperimentResult,
        run_dir: Path,
        report: WriteReport,
    ) -> None:
        if result.ber is None:
            return
        sub = run_dir / Path(self.dir_ber).name
        ensure_dir(sub)
        row = ber_to_row(result.ber)
        if self.enable_json:
            report.add(write_json(row, sub / "ber.json"))
        if self.enable_csv:
            report.add(write_csv_rows([row], sub / "ber.csv"))

    def _write_evm(
        self,
        result: ExperimentResult,
        run_dir: Path,
        report: WriteReport,
    ) -> None:
        if result.evm is None:
            return
        sub = run_dir / Path(self.dir_evm).name
        ensure_dir(sub)
        row = evm_to_row(result.evm)
        if self.enable_json:
            report.add(write_json(row, sub / "evm.json"))
        if self.enable_csv:
            report.add(write_csv_rows([row], sub / "evm.csv"))

    def _write_psd(
        self,
        result: ExperimentResult,
        run_dir: Path,
        report: WriteReport,
    ) -> None:
        if result.psd is None:
            return
        sub = run_dir / Path(self.dir_psd).name
        ensure_dir(sub)
        if self.enable_json:
            report.add(write_json(result.psd.to_dict(), sub / "psd.json"))
        if self.enable_csv:
            report.add(write_csv_rows(psd_to_rows(result.psd), sub / "psd.csv"))
        if self.enable_numpy and self.save_raw_data:
            report.add(
                write_npz(
                    sub / "psd.npz",
                    frequencies=np.asarray(result.psd.frequencies),
                    psd_db=np.asarray(result.psd.psd_db),
                )
            )

    def _write_constellation(
        self,
        result: ExperimentResult,
        run_dir: Path,
        report: WriteReport,
    ) -> None:
        if result.constellation is None:
            return
        sub = run_dir / Path(self.dir_figures).name
        ensure_dir(sub)
        cst = result.constellation
        if self.enable_json:
            report.add(
                write_json(cst.to_dict(), sub / "constellation_meta.json")
            )
        if self.enable_numpy and self.save_raw_data:
            report.add(
                write_npz(
                    sub / "constellation.npz",
                    symbols_real=np.real(np.asarray(cst.symbols)),
                    symbols_imag=np.imag(np.asarray(cst.symbols)),
                    reference_real=np.real(np.asarray(cst.reference_constellation)),
                    reference_imag=np.imag(np.asarray(cst.reference_constellation)),
                )
            )


# =============================================================================
# Batch / multi-SNR helpers
# =============================================================================

def write_ber_curve(
    points: Sequence[BERResult],
    path: PathLike,
    *,
    fmt: str = "csv",
) -> Path:
    """Write a BER-vs-SNR table from many ``BERResult`` objects."""
    rows = [ber_to_row(p) for p in points]
    p = Path(path)
    if fmt == "csv":
        return write_csv_rows(rows, p)
    if fmt == "json":
        return write_json(rows, p)
    raise ValueError(f"Unsupported format: {fmt}")


def write_evm_curve(
    points: Sequence[Tuple[float, EVMResult]],
    path: PathLike,
    *,
    fmt: str = "csv",
) -> Path:
    """``points`` is a sequence of (snr_db, EVMResult)."""
    rows = []
    for snr, evm in points:
        row = evm_to_row(evm)
        row["snr_db"] = float(snr)
        rows.append(row)
    p = Path(path)
    if fmt == "csv":
        return write_csv_rows(rows, p)
    if fmt == "json":
        return write_json(rows, p)
    raise ValueError(f"Unsupported format: {fmt}")


def append_summary_index(
    index_csv: PathLike,
    result: ExperimentResult,
    *,
    run_dir: Optional[PathLike] = None,
) -> Path:
    """
    Append one summary row to a global index CSV (created if missing).
    Useful for aggregating many Monte-Carlo runs.
    """
    p = Path(index_csv)
    row = experiment_summary_row(result)
    if run_dir is not None:
        row["run_dir"] = str(run_dir)
    fieldnames = list(row.keys())
    ensure_dir(p.parent)
    file_exists = p.is_file()
    with p.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow({k: _csv_cell(v) for k, v in row.items()})
    return p


def load_experiment_json(path: PathLike) -> Dict[str, Any]:
    """Load a previously written ``experiment_result.json`` as a plain dict."""
    return read_json(path)


# =============================================================================
# Convenience one-shot API
# =============================================================================

def save_experiment(
    result: ExperimentResult,
    *,
    config: Optional[Any] = None,
    root: Optional[PathLike] = None,
    overwrite: bool = False,
) -> WriteReport:
    """
    One-call helper:

        report = save_experiment(result, config=cfg)
    """
    if config is not None and hasattr(config, "results") and root is None:
        writer = ResultWriter.from_config(config)
        writer.overwrite = overwrite
    else:
        writer = ResultWriter(
            root=Path(root or "results/baseline"),
            overwrite=overwrite,
        )
    return writer.write_experiment(result, config=config)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "utc_now_iso",
    "utc_stamp_for_dirname",
    "ensure_dir",
    "safe_name",
    "run_directory_name",
    "write_json",
    "read_json",
    "write_text",
    "write_csv_rows",
    "write_npz",
    "ber_to_row",
    "evm_to_row",
    "papr_to_row",
    "papr_statistics_to_row",
    "ccdf_to_rows",
    "psd_to_rows",
    "experiment_summary_row",
    "format_text_summary",
    "WriteReport",
    "ResultWriter",
    "write_ber_curve",
    "write_evm_curve",
    "append_summary_index",
    "load_experiment_json",
    "save_experiment",
]
