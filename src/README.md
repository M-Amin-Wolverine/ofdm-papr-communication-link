
# `ofdm_linksim` — Core Python Package

This is the **installable simulation library** for OFDM-PAPR-LinkSim.
Everything under `src/ofdm_linksim/` is what `pip install -e .` exposes as
the `ofdm_linksim` import root.

```text
src/ofdm_linksim/
├── __init__.py              # stable public re-exports
├── config.py                # YAML → ExperimentConfig / ConfigSnapshot
├── output.py                # ResultWriter, JSON/CSV/NPZ persistence
├── source.py                # bit generation
├── modulation.py            # QPSK / QAM map & hard demod
├── ofdm_modulator.py        # grid, IFFT, CP → TransmitFrame
├── ofdm_demodulator.py      # CP remove, FFT, data extract
├── channel.py               # AWGN / Rayleigh / Rician
├── papr.py                  # PAPR measurement on useful samples
├── crc.py                   # optional CRC (identity in Stage-1)
├── channel_coding.py        # encoder (NONE = identity)
├── channel_decoder.py       # decoder (NONE = identity)
├── interleaver.py           # interleave / deinterleave (NONE)
├── equalizer.py             # NONE / ZF / MMSE hooks
├── synchronization.py       # optional impairments (off in Stage-1)
├── core/
│   ├── types.py             # enums, frames, metric dataclasses
│   └── pipeline.py          # OFDMChain orchestration
├── analysis/
│   ├── ber.py
│   ├── ccdf.py
│   ├── evm.py
│   └── psd.py
└── utils/
    ├── random.py            # centralized seeded streams
    └── validation.py        # shared argument checks
```

PAPR **reduction algorithms** (none, clipping, SLM, …) live in the
sibling package [`papr_methods/`](../../papr_methods/) at the repo root,
not inside this tree.

---

## Install

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

```python
import ofdm_linksim
print(ofdm_linksim.__version__)
```

Editable install is recommended while developing blocks under this folder.

---

## Stage-1 scientific baseline (locked)

| Item | Value |
|------|--------|
| Modulation | QPSK, uncoded |
| Channel | AWGN |
| PAPR reduction | `none` (see `papr_methods`) |
| PAPR metric | Useful samples only (CP excluded) |
| Coding / interleaving / EQ / sync impairments | Off (identity) |
| RNG | Centralized streams in `utils.random` |
| Defaults | FFT 256, data 192, CP 16, oversampling 4 |

Canonical config file: `configs/baseline.yaml` (loaded via `config.load_baseline()`).

---

## End-to-end data flow

```text
generate_random_bits
        │
        ▼
modulate  (QPSK / QAM)
        │
        ▼
modulate_ofdm  →  TransmitFrame
        │
        ├──────────►  papr_methods.* / papr.compute_papr
        │
        ▼
apply_channel  →  ChannelOutput
        │
        ▼
demodulate_ofdm  →  OFDMDemodResult
        │
        ▼
demodulate  →  bits
        │
        ▼
analysis.ber / evm / ccdf / psd
        │
        ▼
output.ResultWriter  →  results/
```

Optional Stage-1 identity stages (CRC, coding, interleaver, equalizer,
synchronizer) can be inserted without changing frame types.

---

## Subpackage guide

### `core/`

| Module | Responsibility |
|--------|----------------|
| `types.py` | Contracts: `TransmitFrame`, `OFDMSignal`, `OFDMGrid`, `ChannelOutput`, `PAPRResult`, `BERResult`, `EVMResult`, `ExperimentResult`, enums (`ModulationType`, `ChannelType`, `PAPRMethod`, …), helpers (`make_papr_result`, `db_to_linear`, …) |
| `pipeline.py` | `OFDMChain`, `PipelineComponents`, optional vs required stages, PAPR processor injection |

**Rule:** algorithms do not live here—only types and orchestration.

### `utils/`

| Module | Responsibility |
|--------|----------------|
| `random.py` | `make_rng`, `make_stream_rngs`, `source_rng`, `channel_rng`, `papr_rng`, stream IDs |
| `validation.py` | Shape / finite / length helpers used across blocks |

**Rule:** never call `np.random.seed` or the global `np.random` module inside library code.

### `analysis/`

| Module | Metric |
|--------|--------|
| `ber.py` | `compute_ber`, `aggregate_ber` → `BERResult` |
| `evm.py` | `compute_evm` → `EVMResult` |
| `ccdf.py` | Empirical PAPR CCDF → `CCDFResult` |
| `psd.py` | Welch-style PSD → `PSDResult` |

Pure functions: inputs in, frozen result objects out.

### Transmit / receive blocks (package root)

| Module | Role |
|--------|------|
| `source.py` | Random bits / byte ↔ bit helpers |
| `modulation.py` | Constellation map & hard demod (Gray QPSK / square QAM) |
| `ofdm_modulator.py` | Subcarrier allocation, IFFT, CP, `TransmitFrame` |
| `ofdm_demodulator.py` | CP removal, FFT, grid rebuild, data symbols |
| `channel.py` | AWGN; Rayleigh / Rician ready for Phase-2 |
| `papr.py` | Measurement API on useful samples (`compute_papr`, `get_useful_samples`, …) |
| `crc.py` / `channel_coding.py` / `channel_decoder.py` / `interleaver.py` | Identity in Stage-1; hooks for later codecs |
| `equalizer.py` | `NONE` pass-through; ZF / MMSE stubs for fading |
| `synchronization.py` | Disabled by default; optional CFO / timing hooks |
| `config.py` | Load & validate YAML → `ExperimentConfig` / `ConfigSnapshot` |
| `output.py` | `ResultWriter`, summaries, CSV/JSON/NPZ layout |

---

## Public import style

Prefer the package root for stable symbols:

```python
from ofdm_linksim import (
    modulate,
    demodulate,
    modulate_ofdm,
    demodulate_ofdm,
    apply_channel,
    compute_ber,
    compute_papr,
    load_baseline,
    ResultWriter,
    ModulationType,
    ChannelType,
    TransmitFrame,
)
```

Deep imports are fine for development:

```python
from ofdm_linksim.ofdm_modulator import allocate_subcarriers
from ofdm_linksim.utils.random import make_stream_rngs
```

PAPR **algorithms**:

```python
from papr_methods.none import apply_none
from papr_methods.clipping import apply_clipping
from papr_methods import get_method
```

---

## Minimal library usage

```python
from ofdm_linksim import (
    generate_random_bits,
    modulate,
    demodulate,
    modulate_ofdm,
    demodulate_ofdm,
    apply_channel,
    compute_ber,
    ModulationType,
    ChannelType,
    MappingType,
)
from ofdm_linksim.utils.random import make_stream_rngs
from papr_methods.none import apply_none

streams = make_stream_rngs(42)
n_data, n_blocks, bps = 192, 20, 2
bits = generate_random_bits(n_data * n_blocks * bps, rng=streams["source"])
symbols = modulate(bits, mod=ModulationType.QPSK)

tx = modulate_ofdm(
    symbols,
    source_bits=bits,
    coded_bits=bits,
    interleaved_bits=bits,
    n_data=n_data,
    mapping=MappingType.SYMMETRIC,
)

papr = apply_none(tx, rng=streams["papr"]).papr
ch = apply_channel(tx, snr_db=15.0, rng=streams["channel"], channel_type=ChannelType.AWGN)
rx = demodulate_ofdm(
    ch.signal,
    data_indices=tx.ofdm_grid.data_indices,
    pilot_indices=tx.ofdm_grid.pilot_indices,
    fft_size=tx.waveform.fft_size,
    oversampling=tx.waveform.oversampling,
    cyclic_prefix_length=tx.waveform.cyclic_prefix_length,
    n_symbols=tx.waveform.n_symbols,
    cp_included=tx.waveform.cp_included,
)
rx_bits = demodulate(rx.equalized_symbols, mod=ModulationType.QPSK)
ber = compute_ber(bits[: rx_bits.size], rx_bits, snr_db=15.0)

print(papr.papr_db, ber.ber)
```

---

## Configuration & results

```python
from ofdm_linksim import load_baseline, ResultWriter

cfg = load_baseline()                    # configs/baseline.yaml
cfg.simulation.mode = "development"      # fewer blocks while debugging

writer = ResultWriter.from_config(cfg)
# writer.write_experiment(experiment_result, config=cfg)
```

See `config.py` for section dataclasses and reference-constraint checks.
See `output.py` for directory layout under `results/`.

---

## Testing this package

```bash
# once unit tests exist
pytest tests/unit -q
pytest tests/integration -q
```

Until tests are filled, use:

```bash
python examples/full_link.py
python examples/baseline_papr.py
python examples/baseline_ber.py
```

---

## Extension guidelines

1. **New metric** → `analysis/<name>.py` + result dataclass in `core.types`.
2. **New channel model** → extend `channel.py` + `ChannelType` enum.
3. **New PAPR algorithm** → implement under `papr_methods/`, not here; only
   share measurement helpers via `papr.py`.
4. **Keep Stage-1 identity blocks** side-effect free when disabled.
5. **Frozen / validated results** — prefer existing `*Result` types over ad-hoc dicts.
6. **No hidden global state** — pass `rng`, config, and frames explicitly.

---

## Related documentation

- Project overview: [`../../README.md`](../../README.md)
- Examples: [`../../examples/README.md`](../../examples/README.md)
- Scripts: [`../../scripts/README.md`](../../scripts/README.md)
- PAPR methods: [`../../papr_methods/README.md`](../../papr_methods/README.md)
- Baseline YAML: [`../../configs/baseline.yaml`](../../configs/baseline.yaml)

---

## License

Same as the main project (see repository `LICENSE`).
