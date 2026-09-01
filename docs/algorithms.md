# PAPR Algorithms

This document describes reduction methods and how they connect to measurement
APIs. Measurement rules are defined in [`metrics.md`](metrics.md).

## Measurement vs reduction

| Concern | Location |
|---------|----------|
| PAPR / useful samples / statistics | `ofdm_linksim.papr` |
| CCDF of PAPR | `ofdm_linksim.analysis.ccdf` |
| Reduction algorithms | `papr_methods/` |

Reduction modules should expose:

- `apply_*` → processed waveform + `PAPRResult` (research API)
- `process(transmit_frame, *, rng=None, **kwargs) → PAPRResult` (pipeline API)

## Stage-1: `none` (locked reference)

**Behaviour:** identity. No change to the OFDM time-domain signal.

**Use:** scientific reference against which every algorithm is compared.

```text
TransmitFrame / OFDMSignal
        → apply_none / process
        → PAPRResult (cp_excluded=true)
```

Module: `papr_methods/none.py`  
Scenario: locked baseline (`papr.method: none`)

## Stage-1: `clipping`

**Behaviour:** limit instantaneous amplitude.

Hard clip:

$$\[
x \leftarrow
\begin{cases}
A\,e^{j\arg(x)} & |x| > A \\
x & \text{otherwise}
\end{cases}
\]$$

Soft clip (optional): $$\(A\tanh(|x|/A)\,e^{j\arg(x)}\)$$.

Clipping ratio:

$$\[
CR = \frac{A}{\mathrm{rms}}
,\qquad
\mathrm{rms}=\sqrt{\mathbb{E}[|x|^2]}
\]$$

with $$\(\mathrm{rms}\)$$ computed on **useful** samples. Typical grid:
$$\(CR \in \{1.2, 1.4, 1.6, 1.8, 2.0\}\)$$.

**Trade-off:** PAPR ↓ , in-band distortion ↑ $$(EVM/BER)$$.

Module: `papr_methods/clipping.py`  
Scenario: `scenarios/papr/clipping.yaml`  
Sweep CLI: `scripts/run_papr_sweep.py`

## Phase-2 stubs (layout only)

These modules exist for package completeness. Public APIs raise
`NotImplementedError` in Stage-1.

| Method | Principle | Planned knobs | Module |
|--------|-----------|---------------|--------|
| **SLM** | Multiple candidate phase rotations; select lowest PAPR | `n_candidates`, phase set | `slm.py` |
| **PTS** | Partition into sub-blocks; optimize sub-block phases | `n_subblocks`, candidates | `pts.py` |
| **Tone Reservation** | Reserved tones synthesize peak-cancelling signal | reserved indices, iterations | `tone_reservation.py` |
| **ACE** | Extend outer constellation points away from boundaries | iterations, max extension | `ace.py` |

Scenario YAML stubs under `scenarios/papr/` mirror these names.

## Fair comparison protocol

1. Identical numerology (FFT, CP, oversampling, data tones) unless the study
   is explicitly a numerology sweep (`profiles/ieee80211a`, `nr_like`).
2. Identical seed / stream policy.
3. Same PAPR definition (useful samples, CP excluded).
4. Always include **`none`** on CCDF plots.
5. Report ΔPAPR **and** BER/EVM at matched SNRs for distorting methods
   (especially clipping).

## Registry

```python
from papr_methods import get_method, list_methods

fn = get_method("none")       # or PAPRMethod.NONE
papr_result = fn(transmit_frame, rng=papr_rng)
```

Unknown or unimplemented methods must fail loudly (no silent fallback to
`none` in research runs).
