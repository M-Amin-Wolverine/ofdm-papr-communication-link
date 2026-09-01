# Experiments

Research drivers live under [`experiments/`](../experiments/) and are thicker
than `examples/`. CLI helpers also exist under [`scripts/`](../scripts/).

## Planned / placeholder study scripts

| Script | Goal |
|--------|------|
| `experiments/ber_vs_snr.py` | Uncoded QPSK-OFDM BER curve over AWGN |
| `experiments/papr_ccdf.py` | Empirical PAPR CCDF for `none` (and clipping) |
| `experiments/parameter_sweep.py` | Numerology / CR / block-count sweeps |
| `experiments/benchmark.py` | Throughput / scaling checks |

Until filled, use:

```bash
python examples/baseline_ber.py --sweep 0 20 2
python examples/baseline_papr.py --compare-clip
python scripts/run_papr_sweep.py --methods none,clipping
python scripts/run_baseline.py
```
