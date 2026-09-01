# Examples — OFDM-PAPR-LinkSim

Runnable Stage-1 scripts that exercise the end-to-end OFDM link and the
PAPR analysis path without requiring the full experiment harness.

These examples are intentionally small, deterministic (seeded RNG), and
aligned with the **locked Research Baseline**:

| Item              | Value                          |
|-------------------|--------------------------------|
| Modulation        | QPSK (uncoded)                 |
| Channel           | AWGN                           |
| PAPR method       | `none` (optional clipping)     |
| PAPR measurement  | Useful samples only (no CP)   |
| FFT size (default)| 256                            |
| Data subcarriers  | 192                            |
| Cyclic prefix     | 16 original-rate samples       |
| Oversampling      | 4                              |

---

## Installation

From the repository root:

```bash
# recommended: editable install
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .

# minimal dependencies (if not using pyproject extras)
pip install -r requirements.txt
```

The examples also prepend `src/` and the repo root to `sys.path`, so they
can often be run **without** an install during development:

```bash
python examples/full_link.py
```

For a clean environment, prefer `pip install -e .`.

---

## Quick start

```bash
# full TX → channel → RX link + BER / EVM / PAPR
python examples/full_link.py
python examples/full_link.py --snr 12 --blocks 30 --seed 42

# PAPR reference (none) and optional clipping comparison
python examples/baseline_papr.py
python examples/baseline_papr.py --compare-clip --clip 1.4 --blocks 200

# BER at one SNR or a small sweep
python examples/baseline_ber.py
python examples/baseline_ber.py --snr 10 --blocks 50
python examples/baseline_ber.py --sweep 0 20 4 --blocks 30
```

---

## What each script does

### `full_link.py`

**Purpose:** Single end-to-end demonstration of the Stage-1 communication chain.

**Pipeline:**

1. Generate random bits (centralized `source` RNG stream)
2. QPSK modulation
3. OFDM modulation (IFFT + cyclic prefix, symmetric subcarrier map)
4. PAPR measurement with method **`none`** (useful samples only)
5. AWGN channel at a chosen SNR
6. OFDM demodulation (CP removal + FFT + data-tone extraction)
7. QPSK hard demodulation
8. Report **BER**, **RMS EVM**, and **PAPR**

**Useful flags:**

| Flag            | Meaning                              | Default |
|-----------------|--------------------------------------|---------|
| `--seed`        | Master seed                          | 42      |
| `--snr`         | Channel SNR in dB (Es/N0)            | 20      |
| `--blocks`      | Number of OFDM symbols               | 20      |
| `--fft-size`    | FFT size                             | 256     |
| `--n-data`      | Data subcarriers                     | 192     |
| `--cp`          | CP length (original-rate samples)    | 16      |
| `--oversampling`| Oversampling factor                  | 4       |

**When to use it:** First smoke test after changing core TX/RX code.

---

### `baseline_papr.py`

**Purpose:** Focused PAPR experiment on the **transmit** waveform (no channel required for the reference metric).

**Pipeline:**

1. Build the same Stage-1 OFDM transmit frame as above
2. Run `papr_methods.none` → reference PAPR
3. Optionally run `papr_methods.clipping` and print ΔPAPR
4. Optionally collect per-block PAPR values (`--collect N`) for a quick
   empirical distribution summary (mean / median / max / min)

**Useful flags:**

| Flag              | Meaning                                         | Default |
|-------------------|-------------------------------------------------|---------|
| `--blocks`        | OFDM symbols                                    | 100     |
| `--compare-clip`  | Also run hard clipping                          | off     |
| `--clip`          | Clipping ratio \(CR = A / \mathrm{rms}\)        | 1.5     |
| `--collect N`     | Summarize per-symbol PAPR for `N` symbols       | 0       |

**When to use it:** Validate PAPR definitions, CP exclusion, and clipping
behaviour before larger CCDF campaigns.

---

### `baseline_ber.py`

**Purpose:** Uncoded QPSK-OFDM **BER** over AWGN at one SNR or a small sweep.

**Pipeline (per SNR point):**

1. Seeded bit generation and QPSK mapping
2. OFDM TX
3. AWGN at that SNR
4. OFDM RX + QPSK demod
5. `compute_ber(tx_bits, rx_bits)`

**Useful flags:**

| Flag                         | Meaning                          | Default |
|------------------------------|----------------------------------|---------|
| `--snr`                      | Single operating point (dB)      | 12      |
| `--sweep START STOP STEP`    | SNR grid via `numpy.arange`      | off     |
| `--blocks`                   | OFDM symbols **per SNR point**   | 40      |

**When to use it:** Sanity-check the link against expected QPSK-AWGN trends
(BER should generally fall as SNR increases; use more `--blocks` for smoother curves).

---

## Design notes (shared by all examples)

1. **Reproducibility** — All randomness goes through `ofdm_linksim.utils.random`
   named streams (`source`, `channel`, `papr`, …). Do not call `np.random.seed`
   inside examples.
2. **Stage-1 identity blocks** — Coding, interleaving, equalization, and
   synchronization impairments are disabled (pass-through).
3. **PAPR contract** — Peak-to-average power ratio is measured on **useful**
   samples only; the cyclic prefix is excluded.
4. **Defaults** — Match `configs/baseline.yaml` / `core.types` defaults where possible.
5. **Not a full Monte-Carlo harness** — For large block counts, SNR campaigns,
   and result archiving, prefer `scripts/run_baseline.py`,
   `scripts/run_experiment.py`, and the `experiments/` package once those are filled.

---

## Expected output (illustrative)

Successful runs print a short text report, for example:

```text
================================================================
OFDM-PAPR-LinkSim — Stage-1 full link
================================================================
  seed            : 42
  modulation      : QPSK
  channel         : AWGN
  SNR (dB)        : 20.00
  ...
  PAPR            : 8.xxxx dB
  BER             : x.xxe-xx
  RMS EVM         : x.xxxx %
================================================================
```

Exact numbers depend on seed, block count, and SNR.

---

## Troubleshooting

| Symptom | What to check |
|--------|----------------|
| `ModuleNotFoundError: ofdm_linksim` | Run from repo root or `pip install -e .` |
| `ModuleNotFoundError: papr_methods` | Repo root must be on `PYTHONPATH` (examples add it automatically) |
| `NotImplementedError` from SLM/PTS/… | Stage-1 only supports `none` and `clipping` |
| BER stuck near 0.5 | SNR too low or demod path broken — try `--snr 20 --blocks 20` |
| PAPR changes when only CP length changes | Ensure you still measure **useful** samples only |

---

## Related documentation

- Project overview: [`../README.md`](../README.md)
- Locked baseline config: [`../configs/baseline.yaml`](../configs/baseline.yaml)
- PAPR methods package: [`../papr_methods/`](../papr_methods/)
- Core API: [`../src/ofdm_linksim/`](../src/ofdm_linksim/)

---

## License

Same as the main project (see repository `LICENSE`).

---
