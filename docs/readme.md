# Documentation — OFDM-PAPR-LinkSim

All documentation and technical references live under this folder.

```text
docs/
├── baseline.md          # Locked Stage-1 scientific baseline (core)
├── architecture.md      # High-level architecture and pipeline
├── algorithms.md        # PAPR reduction methods & research approach
├── methodology.md       # Experimental methodology, reproducibility, metrics
├── experiments.md       # Planned study drivers (BER curves, CCDF, etc.)
└── README.md            # this file
```

---

## Locked Stage-1 Baseline (the foundation)

The **entire project** is built around the following locked scientific baseline:

- **Modulation**: QPSK (uncoded)
- **Channel**: AWGN only (Rayleigh / Rician in Phase-2)
- **PAPR reduction**: `none` (locked reference); `clipping` is the only executable reduction in Stage-1
- **PAPR measurement**: Always on **useful samples only** (cyclic prefix excluded)
- **RNG**: Centralized seeded streams via `ofdm_linksim.utils.random`
- **Coding / Interleaving / Equalization / Synchronization**: Identity (disabled / pass-through)

### Core References

| Reference | File | Purpose |
|-----------|------|---------|
| IEEE 802.11ax-2021 | `references/IEEE_802_11ax.pdf` | Official OFDM/OFDMA waveform structure, subcarrier mapping, PAPR rules, clipping & tone reservation |
| MATLAB Communications Toolbox | `references/MATLAB_PAPR_toolbox.pdf` | Reference implementation of OFDM modulation, PAPR estimation & reduction algorithms |
| Rappaport (2022) | `references/Rappaport_2022.pdf` | Textbook fundamentals of OFDM and multi-carrier modulation |

All other references (survey papers, classic clipping/TR papers, etc.) support the narrative and future experiments. The **core scientific baseline** is defined strictly by the two documents above.

---

## Documentation Structure

| Document | Purpose |
|----------|---------|
| `baseline.md` | Locked parameters, constraints, and scientific reference numbers |
| `architecture.md` | Pipeline overview (`source` → `modulation` → `ofdm_modulator` → `channel` → `ofdm_demodulator` → `analysis`) and Stage-1 identity blocks |
| `algorithms.md` | PAPR reduction methods (`none`, `clipping`, Phase-2 stubs: SLM/PTS/TR/ACE) with parameters and performance trade-offs |
| `methodology.md` | Reproducibility policy, metric definitions, CCDF / BER / EVM / PSD conventions, and experiment protocol |
| `experiments.md` | Planned research studies, sweep configurations, and how results are written |

---

## How to use

1. Read `baseline.md` first — it contains the locked scientific contract.
2. Follow the architecture diagram in `architecture.md` for understanding the pipeline.
3. Use `algorithms.md` when implementing or comparing PAPR reduction methods.
4. `methodology.md` and `experiments.md` guide experiment design and result analysis.

---

## Related documentation

- Project overview: [`../README.md`](../README.md)
- PAPR methods: [`../papr_methods/README.md`](../papr_methods/README.md)
- Scenarios: [`../scenarios/README.md`](../scenarios/README.md)
- Scripts: [`../scripts/README.md`](../scripts/README.md)
- Baseline config: [`../configs/baseline.yaml`](../configs/baseline.yaml)

---

## License

Same as the main project (see repository `LICENSE`)
