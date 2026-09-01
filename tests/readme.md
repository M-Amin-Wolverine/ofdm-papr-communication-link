# Tests — OFDM-PAPR-LinkSim

```text
tests/
├── unit/                 # Pure functions / single blocks
│   ├── test_source.py
│   ├── test_modulation.py
│   ├── test_ofdm_modulator.py
│   ├── test_ofdm_demodulator.py
│   ├── test_channel.py
│   ├── test_papr.py
│   ├── test_metrics.py          # BER / EVM / CCDF / PSD helpers
│   ├── test_crc.py
│   ├── test_channel_coding.py
│   ├── test_interleaver.py
│   ├── test_equalizer.py
│   └── test_synchronization.py
├── integration/
│   ├── test_baseline_link.py    # TX → channel → RX → BER path
│   └── test_baseline_papr.py    # PAPR none / useful-sample policy
└── performance/
    └── test_benchmark.py        # Timing / scale smoke (optional)
```

## Status (Stage-1)

All listed modules currently exist as **empty placeholders**.  
Implementations should be filled in dependency order:

1. `unit/test_source.py`, `test_modulation.py`
2. `test_ofdm_modulator.py`, `test_ofdm_demodulator.py`
3. `test_channel.py`, `test_papr.py`, `test_metrics.py`
4. identity blocks (`crc`, `channel_coding`, `interleaver`, `equalizer`, `synchronization`)
5. `integration/test_baseline_link.py`, `test_baseline_papr.py`
6. `performance/test_benchmark.py` (last)

## How to run

```bash
pip install -e ".[dev]"   # or: pip install pytest numpy
pytest tests/unit -q
pytest tests/integration -q
pytest tests/ -q
```

## Conventions

- Prefer **pytest** style (`test_*` functions).
- Use **fixed seeds** via `ofdm_linksim.utils.random` (no global `np.random.seed`).
- Stage-1 expectations: uncoded QPSK, AWGN, PAPR on **useful samples only**, CP excluded.
- Integration tests should stay **small** (few OFDM symbols) so CI stays fast.

## Related

- Package: `src/ofdm_linksim/`
- Examples (manual smoke): `examples/`
- Scripts: `scripts/run_baseline.py`

