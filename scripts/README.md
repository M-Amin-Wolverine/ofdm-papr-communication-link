# Scripts — OFDM-PAPR-LinkSim

Command-line entry points for **reproducible research runs**, heavier than
the short demos under `examples/`.

```text
scripts/
├── run_baseline.py        # Stage-1 locked baseline runner
├── run_experiment.py      # Generic scenario / config runner (in progress)
├── run_papr_sweep.py      # PAPR / SNR / parameter sweeps (placeholder)
├── validate_results.py    # Result integrity checks (placeholder)
└── README.md              # this file
```

| Script                 | Status (Stage-1) | Role |
|------------------------|------------------|------|
| `run_baseline.py`      | Implemented      | Locked QPSK + AWGN + PAPR `none` |
| `run_experiment.py`    | Partial          | Load YAML scenario and write results |
| `run_papr_sweep.py`    | Placeholder      | Multi-point PAPR / method campaigns |
| `validate_results.py`  | Placeholder      | Post-run validation of result folders |

For quick interactive checks, prefer `examples/` first. Use `scripts/` when
you need config-driven runs, result trees under `results/`, and longer
Monte-Carlo campaigns.

---

## Prerequisites

From the **repository root**:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
# or: pip install -r requirements.txt
```

Scripts expect to import:

- `ofdm_linksim` (from `src/`)
- `papr_methods` (repo-root package)
- optional YAML via `PyYAML` (`load_baseline` / `load_config`)

Always run commands from the repository root so relative paths such as
`configs/baseline.yaml` and `results/baseline` resolve correctly.

```bash
cd /path/to/ofdm-papr-communication-link
python scripts/run_baseline.py --help
```

---

## Design principles

1. **Config-driven** — Prefer `configs/baseline.yaml` (and later
   `scenarios/*.yaml`) over hard-coded magic numbers.
2. **Reproducible RNG** — Use `ofdm_linksim.utils.random` streams only.
3. **PAPR contract** — Measure on **useful samples** (CP excluded).
4. **Stage-1 defaults** — Uncoded QPSK, AWGN, PAPR method `none`, no
   sync impairments, no interleaving.
5. **Artifacts** — Write through `ofdm_linksim.output.ResultWriter` when
   possible (`results/...` layout, JSON/CSV/NPZ + summary).
6. **CLI** — `argparse`, exit code `0` on success, non-zero on failure.

---

## `run_baseline.py`

### Purpose

Run the **locked Stage-1 research baseline**:

- Modulation: QPSK (uncoded)
- Channel: AWGN
- PAPR reduction: none
- Metrics: BER, EVM, PAPR (and related fields when wired)

This is the reference experiment against which clipping / SLM / PTS / …
will later be compared.

### Usage

```bash
python scripts/run_baseline.py
python scripts/run_baseline.py --seed 42 --snr 20 --blocks 1000
python scripts/run_baseline.py --output results/baseline
```

### Typical flags

| Flag        | Meaning                         | Notes |
|-------------|----------------------------------|-------|
| `--seed`    | Master experiment seed           | Must stay fixed for reproducibility |
| `--snr`     | Operating SNR (dB)               | Es/N0 under baseline definition |
| `--blocks`  | Number of OFDM symbols / blocks  | Larger → better PAPR tail stats |
| `--output`  | Results root directory           | Default under `results/baseline` |

Exact flag names follow the script’s `argparse` definition; run
`--help` after updates.

### Outputs

When fully wired to `ResultWriter` / `ExperimentResult`:

```text
results/baseline/
└── <scenario>__seed<seed>__<run_id>__<timestamp>/
    ├── experiment_result.json
    ├── summary.json / summary.csv / summary.txt
    ├── metadata/
    ├── papr/
    ├── ber/
    └── ...
```

### When to use

- Smoke-test the installed package after a pull
- Produce the official Stage-1 reference numbers
- Feed `validate_results.py` once that script is implemented

---

## `run_experiment.py`

### Purpose

Generic runner for **non-locked** or **alternative** scenarios:

- Custom YAML under `scenarios/` or `configs/`
- Different SNR, seeds, output roots
- Future channel models (Rayleigh / Rician) and PAPR methods

### Status

Currently a **partial implementation**: it loads configuration and defines
the CLI skeleton; the full pipeline body may still need completion so that
a real `ExperimentResult` is built end-to-end.

### Intended usage

```bash
python scripts/run_experiment.py \
  --scenario scenarios/baseline.yaml \
  --seed 42 \
  --snr 15 \
  --output results/experiments
```

### Planned flags

| Flag          | Meaning                              |
|---------------|--------------------------------------|
| `--scenario`  | Path to scenario / config YAML       |
| `--seed`      | Master seed                          |
| `--snr`       | Single SNR override (dB)             |
| `--output`    | Results root                         |

### When to use

- After Stage-1 baseline is stable
- When comparing multiple YAML profiles without editing code
- As the parent entry point for batch jobs / CI

---

## `run_papr_sweep.py` (placeholder)

### Purpose

Batch campaigns over PAPR-related axes, for example:

- PAPR method: `none`, `clipping` (later SLM, PTS, …)
- Clipping ratio grid
- FFT size / oversampling / block count
- Empirical CCDF at baseline probabilities \(10^{-1}\ldots10^{-4}\)

### Status

File exists but is **not implemented** yet (empty placeholder).

### Target usage (planned)

```bash
python scripts/run_papr_sweep.py \
  --methods none,clipping \
  --clip-ratios 1.2,1.4,1.6,1.8 \
  --blocks 10000 \
  --output results/experiments/papr_sweep
```
OR

```bash
python scripts/run_papr_sweep.py --blocks 100 --methods none,clipping
python scripts/run_papr_sweep.py --clip-ratios 1.3,1.5 --save-raw
python scripts/validate_results.py results/experiments/papr_sweep --recursive
python scripts/validate_results.py results/baseline --recursive --strict
```

### When to implement

After `examples/baseline_papr.py` and `papr_methods.clipping` are validated
on small block counts.

---

## `validate_results.py` (placeholder)

### Purpose

Post-process a results directory and check scientific / technical invariants:

- Required files present (`summary.json`, `metadata`, …)
- `PAPRResult` consistency (`papr_db` ↔ `papr_linear`)
- CP excluded flag set
- Config fingerprint matches locked baseline when required
- BER in \([0, 1]\), finite PAPR, positive sample counts

### Status

Placeholder — not implemented yet.

### Target usage (planned)

```bash
python scripts/validate_results.py results/baseline/<run_dir>
python scripts/validate_results.py results/baseline --recursive
```

Exit `0` if all checks pass; non-zero with a clear report otherwise.

---

## Scripts vs examples vs experiments

| Layer          | Path             | Intent |
|----------------|------------------|--------|
| **Examples**   | `examples/`      | Short, educational, few blocks, print to stdout |
| **Scripts**    | `scripts/`       | CLI runners, config paths, write under `results/` |
| **Experiments**| `experiments/`   | Research study drivers (BER curves, CCDF papers, benchmarks) |

Typical workflow:

```text
examples/full_link.py          → does the chain work at all?
scripts/run_baseline.py        → produce a stored baseline run
scripts/run_papr_sweep.py      → systematic PAPR study
experiments/papr_ccdf.py       → publication-oriented analysis
scripts/validate_results.py    → gate results before citing numbers
```

---

## Environment variables (optional conventions)

Scripts should not require env vars, but the following conventions are useful:

| Variable                 | Meaning |
|--------------------------|---------|
| `OFDM_LINKSim_SEED`      | Override default seed if CLI flag omitted |
| `OFDM_LINKSim_RESULTS`   | Default results root |
| `OFDM_LINKSim_CONFIG`    | Default YAML path |

Prefer CLI flags for anything that must appear in paper reproducibility notes.

---

## Troubleshooting

| Symptom | Action |
|--------|--------|
| `ModuleNotFoundError: ofdm_linksim` | `pip install -e .` from repo root |
| `ModuleNotFoundError: papr_methods` | Ensure repo root is on `PYTHONPATH` / installed layout includes it |
| `FileNotFoundError: configs/baseline.yaml` | Run from repository root |
| Empty or tiny `run_papr_sweep.py` | Still a placeholder — use `examples/baseline_papr.py` for now |
| Non-reproducible PAPR/BER | Check seed flags and that no code calls global `np.random` |
| `NotImplementedError` (SLM/PTS/…) | Stage-1 only supports `none` and `clipping` |

---

## Related documentation

- Examples: [`../examples/README.md`](../examples/README.md)
- PAPR methods: [`../papr_methods/README.md`](../papr_methods/README.md)
- Baseline config: [`../configs/baseline.yaml`](../configs/baseline.yaml)
- Output writer API: `src/ofdm_linksim/output.py`
- Config loader API: `src/ofdm_linksim/config.py`
- Project overview: [`../README.md`](../README.md)

---

## License

Same as the main project (see repository `LICENSE`).
```

