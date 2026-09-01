# Tests — OFDM-PAPR-LinkSim

Automated checks for the Stage-1 OFDM / PAPR research baseline.

```text
tests/
├── unit/                              # Single-block / pure-function tests
│   ├── test_source.py
│   ├── test_modulation.py
│   ├── test_ofdm_modulator.py
│   ├── test_ofdm_demodulator.py
│   ├── test_channel.py
│   ├── test_papr.py
│   ├── test_metrics.py                # BER, EVM, CCDF (and related helpers)
│   ├── test_crc.py
│   ├── test_channel_coding.py
│   ├── test_interleaver.py
│   ├── test_equalizer.py
│   └── test_synchronization.py
├── integration/
│   ├── test_baseline_link.py          # TX → AWGN → RX → BER
│   └── test_baseline_papr.py          # PAPR on useful samples (CP excluded)
└── performance/
    └── test_benchmark.py              # Moderate-scale timing smoke tests
```

---

## Status (Stage-1)

| Layer | Scope | Intent |
|-------|--------|--------|
| **unit** | One module at a time | Correctness of contracts, identity blocks, metrics |
| **integration** | Short end-to-end chain | Baseline link + PAPR policy still hold together |
| **performance** | ~tens of OFDM symbols | Catch pathological slowdowns; **not** hard latency SLOs |

Scientific expectations locked for these tests:

- Uncoded **QPSK**
- **AWGN** channel (unless a test explicitly says otherwise)
- PAPR measured on **useful samples only** (cyclic prefix excluded)
- Reproducible RNG via `ofdm_linksim.utils.random` (no global `np.random.seed`)

Identity stages in Stage-1 (`coding`, `interleaving`, `equalization`, `synchronization`, optional CRC paths) are tested as **pass-through** when disabled / `NONE`.

---

## Install & run

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # or: pip install -e . pytest numpy
```

```bash
# all tests
pytest tests/ -q

# by layer
pytest tests/unit -q
pytest tests/integration -q
pytest tests/performance -q

# skip slow timing smoke in fast CI
pytest tests/ -q -m "not performance"

# only integration
pytest tests/ -q -m integration
```

Suggested markers (already used in performance / integration modules):

```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
  "integration: end-to-end Stage-1 path tests",
  "performance: moderate-scale timing / throughput smoke tests",
]
```

---

## What each layer covers

### Unit

| File | Primary target |
|------|----------------|
| `test_source.py` | Bit generation, dtype / length, seeded streams |
| `test_modulation.py` | QPSK (and related) map ↔ hard demod round-trip |
| `test_ofdm_modulator.py` | Grid, IFFT, CP, `TransmitFrame` shape metadata |
| `test_ofdm_demodulator.py` | CP removal, FFT, data-tone extraction |
| `test_channel.py` | AWGN path returns compatible signal layout |
| `test_papr.py` | Useful-sample policy, finite PAPR ≥ 0 dB / ≥ 1 linear |
| `test_metrics.py` | BER / EVM / CCDF basic invariants |
| `test_crc.py` | Encode / check when CRC utilities are enabled |
| `test_channel_coding.py` | `NONE` identity encode / decode |
| `test_interleaver.py` | `NONE` identity interleave / deinterleave |
| `test_equalizer.py` | `NONE` identity equalize |
| `test_synchronization.py` | Disabled / `NONE` path leaves waveform intact |

### Integration

| File | Checks |
|------|--------|
| `test_baseline_link.py` | Small Monte-Carlo-style chain; BER at high SNR stays low |
| `test_baseline_papr.py` | PAPR uses fewer samples than full CP-bearing waveform |

Keep integration **small** (few OFDM symbols) so default CI stays fast.

### Performance

| File | Checks |
|------|--------|
| `test_benchmark.py` | Soft wall-clock bounds for TX, PAPR, and a short full link; rough linear scaling |

Failures here usually mean algorithmic regressions (e.g. accidental Python loops over huge arrays), not “machine too slow.”

---

## Conventions for new tests

1. **pytest** style: functions named `test_*`, optional `@pytest.mark.integration` / `@pytest.mark.performance`.
2. **Seeds**: build RNGs with `make_stream_rngs(seed)` and pass the named stream (`source`, `channel`, `papr`, …).
3. **Assert contracts**, not paper-perfect BER curves (unit/integration are correctness gates; large CCDF campaigns belong in `scripts/` / `experiments/`).
4. Prefer **public package APIs** (`ofdm_linksim.*`, `papr_methods.*`) over private `_helpers` unless testing that helper is the point.
5. If a Phase-2 method is still a stub (`SLM`, `PTS`, …), assert `NotImplementedError` — do not skip silently.

---

## Continuous integration (recommended)

Minimal job:

```bash
pip install -e ".[dev]"
pytest tests/unit tests/integration -q
```

Nightly or manual:

```bash
pytest tests/performance -q
```

---

## Manual smoke (outside pytest)

When debugging a single change without the full suite:

```bash
python examples/full_link.py --blocks 20 --snr 20
python examples/baseline_papr.py --blocks 50
python examples/baseline_ber.py --snr 12 --blocks 40
```

---

## Related documentation

- Package: [`../src/ofdm_linksim/README.md`](../src/ofdm_linksim/README.md)
- Examples: [`../examples/README.md`](../examples/README.md)
- Scripts: [`../scripts/README.md`](../scripts/README.md)
- PAPR methods: [`../papr_methods/README.md`](../papr_methods/README.md)
- Baseline config: [`../configs/baseline.yaml`](../configs/baseline.yaml)

---

## License

Same as the main project (see repository `LICENSE`).
