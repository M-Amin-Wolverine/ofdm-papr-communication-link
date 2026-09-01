# PAPR Methods — OFDM-PAPR-LinkSim

This package implements **Peak-to-Average Power Ratio (PAPR) reduction
algorithms** and the locked **Stage-1 reference** (no reduction).

Location in the repository:

```text
papr_methods/
├── __init__.py           # registry + public exports
├── none.py               # Stage-1 reference (identity + measure)
├── clipping.py           # hard / soft amplitude clipping
├── slm.py                # Selected Mapping          (Phase-2 stub)
├── pts.py                # Partial Transmit Sequence (Phase-2 stub)
├── tone_reservation.py   # Tone Reservation          (Phase-2 stub)
├── ace.py                # Active Constellation Extension (Phase-2 stub)
└── README.md             # this file
```

---

## Role in the system

```text
OFDM modulator
      │
      ▼
TransmitFrame / OFDMSignal
      │
      ▼
papr_methods.<algorithm>     ← this package
      │
      ├── modified waveform (optional)
      └── PAPRResult (always on useful samples)
      │
      ▼
channel / analysis / experiments
```

**Project contract (locked):**

- PAPR is measured on **useful (non-CP) samples only**.
- Stage-1 scientific reference is **`none`** (`PAPRMethod.NONE`).
- All reduction methods are compared against that reference.
- Randomness, if any, must use the injected `rng` (papr stream), never global `np.random`.

---

## Installation / import path

From the repository root:

```bash
pip install -e .
```

The package lives at the **repo root** (sibling of `src/`), not under
`src/ofdm_linksim`. Examples and scripts therefore put the repo root on
`sys.path`. After an editable install, imports work as:

```python
from papr_methods import get_method, list_methods
from papr_methods.none import apply_none, process as process_none
from papr_methods.clipping import apply_clipping, process as process_clipping
```

Measurement helpers used by every method:

```python
from ofdm_linksim.papr import get_useful_samples, compute_papr
from ofdm_linksim.core.types import make_papr_result, PAPRResult, PAPRMethod
```

---

## Common API

Each method module exposes two entry points.

### 1. `apply_<name>(...)` → `PAPRProcessResult`

Full result for research and examples:

| Field       | Type            | Meaning                                      |
|------------|-----------------|----------------------------------------------|
| `waveform` | `ComplexArray`  | Output time-domain samples (may be modified) |
| `papr`     | `PAPRResult`    | Metric on **useful** samples                 |
| `method`   | `PAPRMethod`    | Enum of the algorithm                        |
| `meta`     | `dict`          | Algorithm-specific diagnostics               |

### 2. `process(transmit_frame, *, rng=None, **kwargs)` → `PAPRResult`

Pipeline-facing adapter. The Stage-1 pipeline injects this callable as
`papr_processor` and expects a **`PAPRResult`**.

```python
from papr_methods import get_method
from ofdm_linksim.core.types import PAPRMethod

fn = get_method(PAPRMethod.NONE)       # or "none", "clipping", ...
papr_result = fn(transmit_frame, rng=papr_rng)
```

Registry helpers in `__init__.py`:

```python
from papr_methods import get_method, list_methods

list_methods()          # e.g. ['clipping', 'none', ...]
get_method("clipping")  # returns process_clipping
```

---

## Implemented methods (Stage-1)

### `none.py` — scientific reference

**Behaviour:** Identity. The waveform is **not** modified. PAPR is measured
on useful samples.

**Use when:**

- Establishing the unprocessed OFDM PAPR baseline
- Comparing any reduction algorithm against the locked reference
- Pipeline Stage-1 default (`PAPRMethod.NONE`)

```python
from papr_methods.none import apply_none

result = apply_none(transmit_frame, rng=rng)
print(result.papr.papr_db, result.meta["modified"])  # modified == False
```

---

### `clipping.py` — amplitude clipping

**Behaviour:** Limits the instantaneous amplitude of the time-domain signal.

| Mode   | Rule |
|--------|------|
| `hard` | If \(\lvert x\rvert > A\), set \(x \leftarrow A\,e^{j\arg(x)}\) |
| `soft` | \(A\tanh(\lvert x\rvert/A)\,e^{j\arg(x)}\) |

**Clipping ratio:**

\[
CR = \frac{A}{\sqrt{\mathbb{E}[\lvert x\rvert^2]}}
\]

RMS is computed on **useful** samples. Typical research values: \(CR \in [1.2, 2.0]\).

**Main parameters:**

| Parameter         | Default | Meaning                                      |
|-------------------|---------|----------------------------------------------|
| `clipping_ratio`  | `1.5`   | \(CR = A / \mathrm{rms}\)                    |
| `mode`            | `hard`  | `hard` or `soft`                             |
| `clip_cp`         | `True`  | Clip full waveform including CP              |

PAPR is still reported on useful samples only.

```python
from papr_methods.clipping import apply_clipping

result = apply_clipping(
    transmit_frame,
    clipping_ratio=1.4,
    mode="hard",
    clip_cp=True,
    rng=rng,
)
print(result.papr.papr_db)
print(result.meta["clip_noise_power"], result.meta["amplitude"])
```

**Notes:**

- Clipping reduces PAPR but introduces in-band distortion (higher EVM / BER).
- Always report both ΔPAPR and link metrics when comparing to `none`.

---

## Phase-2 stubs (layout only)

These modules exist so the package is complete and the registry can grow
without renaming files. **Calling them raises `NotImplementedError`.**

| File                    | Method                         | Enum                         |
|-------------------------|--------------------------------|------------------------------|
| `slm.py`                | Selected Mapping               | `PAPRMethod.SLM`             |
| `pts.py`                | Partial Transmit Sequence      | `PAPRMethod.PTS`             |
| `tone_reservation.py`   | Tone Reservation               | `PAPRMethod.TONE_RESERVATION`|
| `ace.py`                | Active Constellation Extension | `PAPRMethod.ACE`             |

Each stub documents planned parameters in the docstring (sub-blocks,
phase sets, reserved tones, iterations, etc.) for future implementation.

```python
from papr_methods.slm import process as process_slm
process_slm(tx_frame)   # → NotImplementedError
```

---

## How methods connect to the rest of the project

| Consumer              | How it uses this package                                      |
|-----------------------|---------------------------------------------------------------|
| `src/.../papr.py`     | Measurement utilities (`get_useful_samples`, `compute_papr`)  |
| `core.pipeline`       | Injects `process` as `papr_processor` → must return `PAPRResult` |
| `examples/baseline_papr.py` | Side-by-side `none` vs `clipping`                         |
| `examples/full_link.py`     | Default PAPR via `apply_none`                             |
| `configs/baseline.yaml`     | `papr_reduction: none`                                    |
| `experiments/` / `scripts/` | Sweep methods, CR values, CCDF curves (once filled)     |

---

## Minimal working example

```python
from ofdm_linksim.source import generate_random_bits
from ofdm_linksim.modulation import modulate
from ofdm_linksim.ofdm_modulator import modulate_ofdm
from ofdm_linksim.core.types import ModulationType, MappingType
from ofdm_linksim.utils.random import make_stream_rngs
from papr_methods.none import apply_none
from papr_methods.clipping import apply_clipping

streams = make_stream_rngs(42)
bits = generate_random_bits(192 * 20 * 2, rng=streams["source"])  # 20 OFDM symbols, QPSK
symbols = modulate(bits, mod=ModulationType.QPSK)
tx = modulate_ofdm(
    symbols,
    source_bits=bits,
    coded_bits=bits,
    interleaved_bits=bits,
    n_data=192,
    mapping=MappingType.SYMMETRIC,
)

ref = apply_none(tx, rng=streams["papr"])
clip = apply_clipping(tx, clipping_ratio=1.5, rng=streams["papr"])

print("PAPR none [dB]:", ref.papr.papr_db)
print("PAPR clip [dB]:", clip.papr.papr_db)
print("Delta [dB]:", ref.papr.papr_db - clip.papr.papr_db)
```

---

## Design rules for new methods

When implementing SLM / PTS / TR / ACE (or a custom algorithm):

1. Accept `TransmitFrame | OFDMSignal | ComplexArray` where practical.
2. Always return metrics via `make_papr_result` on **useful** samples.
3. Accept `rng: np.random.Generator | None` for reproducibility.
4. Provide both `apply_*` → `PAPRProcessResult` and `process` → `PAPRResult`.
5. Register the method in `__init__.py` (`_REGISTRY` / `get_method`).
6. Never call `np.random.seed` or the global `np.random` module.
7. Document distortion side-effects (BER, EVM, spectral regrowth) in `meta`.

---

## Related documentation

- Examples: [`../examples/README.md`](../examples/README.md)
- Core types (`PAPRMethod`, `PAPRResult`): `src/ofdm_linksim/core/types.py`
- PAPR measurement helpers: `src/ofdm_linksim/papr.py`
- Locked baseline: `configs/baseline.yaml`
- Project overview: [`../README.md`](../README.md)

---

## License

Same as the main project (see repository `LICENSE`).

---

این را به‌صورت **`papr_methods/README.md`** commit کن (اگر `none.txt` داخل همان پوشه است، حذفش کن).
