# Methodology

## Reproducibility

1. Fix master seed (default 42) and use stream RNGs only.
2. Persist configuration snapshot with every result directory.
3. Record: seed, FFT, CP, oversampling, modulation, channel, SNR, PAPR method, block count.
4. Prefer `ResultWriter` outputs under `results/` over ad-hoc prints for published numbers.

## Metric definitions

| Metric | Definition notes |
|--------|------------------|
| BER | Bit errors / total bits after hard demod |
| EVM | Error vector vs reference constellation symbols |
| PAPR | Peak-to-average power on useful samples |
| CCDF | Empirical survival function of per-block PAPR (dB) |
| PSD | Spectral estimate (Welch-style when enabled) |

## Experiment protocol (Stage-1)

1. Run locked baseline (`method=none`, AWGN, QPSK) → reference PAPR CCDF and BER vs SNR.
2. Optionally run clipping at one or more \(CR\) values.
3. Compare CCDF tails and BER/EVM at the same SNRs.
4. Validate artifacts with `scripts/validate_results.py`.

## Modes

| Mode | Typical use |
|------|-------------|
| development / smoke | Few blocks; pipeline debug |
| research | Large block counts for CCDF tails |

## What not to claim from Stage-1

- Full 3GPP NR or complete 802.11ax MAC/PHY compliance
- Performance of unimplemented SLM/PTS/TR/ACE
- Fading results from AWGN-only locked baseline
