# Stage-1 Scientific Baseline

This document defines the **locked** research baseline of OFDM-PAPR-LinkSim.
All Stage-1 results, examples, scripts, and tests must remain consistent with
these constraints unless a scenario explicitly marks itself as non-reference.

Canonical machine-readable form: [`configs/baseline.yaml`](../configs/baseline.yaml)  
Scenario entry point: [`scenarios/baseline.yaml`](../scenarios/baseline.yaml)

## Purpose

1. Validate the uncoded OFDM transmit/receive chain.
2. Establish the **unprocessed** OFDM PAPR reference (`method = none`).
3. Provide reproducible BER / EVM / CCDF baselines before comparing reduction algorithms.

## Locked parameters

| Item | Value |
|------|--------|
| Modulation | QPSK (Gray), unit average symbol energy |
| Coding | none (rate 1.0) |
| Interleaving | none |
| Equalization | none (AWGN) |
| Synchronization impairments | off |
| Channel | AWGN only |
| SNR definition | Es/N0 |
| FFT size | 256 |
| Data subcarriers | 192 |
| Pilot subcarriers | 8 (layout reserved; Stage-1 may use zero pilots in some paths) |
| Active subcarriers | 200 |
| Cyclic prefix | 16 original-rate samples |
| Oversampling | 4 (frequency-domain zero-padding) |
| PAPR reduction | **none** |
| PAPR sample set | **useful samples only** (CP excluded) |
| Master seed | 42 (centralized streams) |
| Research block count | 100 000 OFDM symbols (development mode uses fewer) |
| SNR grid (reference) | 0 : 2 : 30 dB |

## Reference constraints

When `scenario.reference: true` (or `load_baseline()` with enforcement):

- uncoded
- no interleaving
- AWGN, no fading
- no sync impairments
- no PAPR reduction (for the locked reference run)
- fixed seed / centralized RNG
- oversampling enabled as configured
- CP excluded from PAPR
- reproducible outputs via config snapshot + seed

## Primary metrics

- PAPR (linear and dB) on useful samples
- Empirical PAPR CCDF at $$\(10^{-1}, 10^{-2}, 10^{-3}, 10^{-4}\)$$
- BER
- RMS EVM (and peak EVM when reported)
- Optional PSD for spectral checks

## Foundational references

Project core references (see [`references/README.md`](../references/README.md)):

- IEEE 802.11ax-related OFDM/OFDMA waveform practice (subcarriers, CP, multi-carrier structure)
- MATLAB Communications Toolbox style OFDM / PAPR tooling documentation

These documents anchor numerology and measurement practice; the **simulator contract** is this baseline file + `configs/baseline.yaml`.

## Non-baseline runs

Allowed in Stage-1 for comparison, but **not** “locked reference” numbers:

- `papr_methods.clipping` / `scenarios/papr/clipping.yaml`
- Profiles `ieee80211a` and `nr_like` (different FFT/CP)
- Development / smoke profiles with reduced block counts

Phase-2 (Rayleigh/Rician, SLM, PTS, TR, ACE) must not overwrite Stage-1 reference claims.
