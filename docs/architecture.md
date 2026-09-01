# PAPR Algorithms

## Measurement (always)

For a discrete-time complex baseband sequence \(x[n]\) on the **useful**
(non-CP) samples:

$$\[
\mathrm{PAPR}
= \frac{\max_n |x[n]|^2}{\mathbb{E}[|x[n]|^2]}
\]$$

Reported in linear scale and in dB: \(10\log_{10}(\mathrm{PAPR})\).

Empirical CCDF:

$$\[
\mathrm{CCDF}(\gamma) = \Pr(\mathrm{PAPR}_{\mathrm{dB}} > \gamma)
\]$$

Standard report probabilities: $$\(10^{-1}, 10^{-2}, 10^{-3}, 10^{-4}\)$$.

## Stage-1 methods

### `none` (locked reference)

- Waveform unchanged.
- PAPR measured on useful samples.
- Scientific baseline for all comparisons.

Implementation: `papr_methods/none.py`

### `clipping`

Hard (or soft) amplitude limit with clipping ratio

$$\[
CR = \frac{A}{\mathrm{rms}}, \quad
\mathrm{rms} = \sqrt{\mathbb{E}[|x|^2]}
\]$$

(computed on useful samples). Typical research grid:$$\(CR \in [1.2, 2.0]\)$$.

Trade-off: lower PAPR, higher in-band distortion (EVM/BER degradation).

Implementation: `papr_methods/clipping.py`

## Phase-2 stubs (not executable in Stage-1)

| Method | Idea | Module |
|--------|------|--------|
| SLM | Candidate phase sequences; pick lowest PAPR | `papr_methods/slm.py` |
| PTS | Sub-block phase optimization | `papr_methods/pts.py` |
| Tone Reservation | Reserved tones cancel peaks | `papr_methods/tone_reservation.py` |
| ACE | Outer constellation extension | `papr_methods/ace.py` |

Calling these raises `NotImplementedError` by design.

## Fair comparison rules

1. Same OFDM numerology, seed policy, and block count family.
2. Same PAPR definition (useful samples, CP excluded).
3. Report **ΔPAPR** and link metrics (BER/EVM), not PAPR alone.
4. Keep `none` as the reference curve on every figure set.

## Scenario hooks

- `scenarios/papr/clipping.yaml`
- `scenarios/papr/slm.yaml`, `pts.yaml`, `tone_reservation.yaml` (stubs)
- CLI sweep: `scripts/run_papr_sweep.py`
