# Metrics

Definitions used by `ofdm_linksim.analysis` and by experiment / script
outputs. All Stage-1 published numbers should follow these conventions.

## Bit Error Rate (BER)

$$\[
\mathrm{BER} = \frac{N_{\mathrm{err}}}{N_{\mathrm{bits}}}
\]$$

- Compare hard-decided receive bits to transmit bits (same length).
- Optional metadata: SNR (dB) at which the measurement was taken.
- Aggregate independent runs by summing errors and bit counts
  (`aggregate_ber`), not by averaging BER ratios blindly.

Implementation: `ofdm_linksim.analysis.ber` → `BERResult`

| Field | Meaning |
|-------|---------|
| `bit_errors` | Number of differing bits |
| `total_bits` | Number of compared bits |
| `ber` | `bit_errors / total_bits` |
| `snr_db` | Optional operating point |

## Error Vector Magnitude (EVM)

Compare complex receive constellation points $$\(y_k\)$$ to reference symbols
$$\(x_k\)$$ (same indexing / length):

$$\[
\mathrm{EVM}_{\mathrm{RMS}}
= \sqrt{
  \frac{\sum_k |y_k - x_k|^2}
       {\sum_k |x_k|^2}
}
\]$$

Often reported as percent: \(100 \times \mathrm{EVM}_{\mathrm{RMS}}\).
Peak EVM may be reported as an additional diagnostic when implemented.

Implementation: `ofdm_linksim.analysis.evm` → `EVMResult`

## Peak-to-Average Power Ratio (PAPR)

For useful (non-CP) complex samples \(x[n]\):

$$\[
\mathrm{PAPR}
= \frac{\max_n |x[n]|^2}{\mathbb{E}[|x[n]|^2]}
,\qquad
\mathrm{PAPR}_{\mathrm{dB}} = 10\log_{10}(\mathrm{PAPR})
\]$$

**Locked rule:** cyclic prefix samples are **excluded** from the average and
the peak search used for the reported metric.

Implementation: `ofdm_linksim.papr` / `make_papr_result` → `PAPRResult`

| Field (typical) | Meaning |
|-----------------|---------|
| `papr_linear` | $$\(\ge 1\)$$ |
| `papr_db` | $$\(10\log_{10}(\mathrm{papr\_linear})\)$$ |
| `n_samples_used` | Count of useful samples |
| `cp_excluded` | Must be `true` for baseline claims |

## Complementary CDF of PAPR (CCDF)

Given per-block PAPR values in dB \(\{p_i\}\):

$$\[
\mathrm{CCDF}(\gamma) = \Pr(P > \gamma) \approx \frac{1}{N}\sum_{i=1}^{N}\mathbf{1}\{p_i > \gamma\}
\]$$

Default report probabilities:

$$\[
\{10^{-1},\,10^{-2},\,10^{-3},\,10^{-4}\}
\]$$

Implementation: `ofdm_linksim.analysis.ccdf` → `CCDFResult`

| Field | Meaning |
|-------|---------|
| `thresholds_db` | Grid of \(\gamma\) |
| `probabilities` | Empirical CCDF values in \([0,1]\) |
| `n_blocks` | Number of PAPR samples |
| `method` | e.g. `empirical` |

## Power Spectral Density (PSD)

When enabled, estimate the spectrum of the time-domain waveform (Welch-style
or project-equivalent). Used for spectral occupancy / regrowth checks when
comparing clipping vs `none`, not as a Stage-1 locked KPI.

Implementation: `ofdm_linksim.analysis.psd` → `PSDResult`

## Throughput (optional / future)

Not a locked Stage-1 primary metric. If reported, define clearly:

$$\[
R = R_b \cdot (1 - \mathrm{BER}) \quad \text{or coded-rate variants}
\]$$

with explicit assumptions (uncoded QPSK, symbol rate, CP overhead).

## Reporting checklist

1. State SNR definition (**Es/N0** in the baseline).
2. State whether PAPR includes CP (**no** for baseline).
3. State block count (CCDF tails need many blocks).
4. Prefer `ResultWriter` artifacts over terminal-only numbers.
5. Validate cited folders with `scripts/validate_results.py`.
