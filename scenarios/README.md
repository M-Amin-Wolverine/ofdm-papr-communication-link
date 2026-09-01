# Scenarios — OFDM-PAPR-LinkSim

YAML **experiment definitions** used by scripts and study drivers.

```text
scenarios/
├── baseline.yaml              # Locked Stage-1 reference scenario
├── papr/                      # PAPR-method oriented scenarios
│   ├── none.yaml
│   ├── clipping.yaml
│   ├── clipping_cr_grid.yaml
│   ├── slm.yaml               # Phase-2 stub
│   ├── pts.yaml
│   ├── tone_reservation.yaml
│   └── ace.yaml
├── profiles/                  # Runtime profiles (block count, sweeps, …)
│   ├── nr_like.yaml
│   └── ieee80211a.yaml
└── README.md
```

---

## `configs/` vs `scenarios/`

| Location | Role |
|----------|------|
| `configs/baseline.yaml` | **Canonical** locked scientific configuration (full detail) |
| `scenarios/baseline.yaml` | Scenario entry point mirroring the locked baseline |
| `scenarios/profiles/*` | Runtime profiles (fewer blocks, BER sweep, …) |
| `scenarios/papr/*` | Method-specific PAPR experiments |

Loaders (`ofdm_linksim.config.load_config` / `load_baseline`) primarily read
`configs/baseline.yaml`. Scenario files are intended for
`scripts/run_experiment.py` and experiment drivers. Fields such as
`extends:` document inheritance intent; the Python loader may deep-merge
overrides depending on implementation version.

---

## Stage-1 executable scenarios

| File | Status | Purpose |
|------|--------|---------|
| `baseline.yaml` | **locked** | Official reference (QPSK, AWGN, PAPR none) |
| `papr/none.yaml` | active | Explicit PAPR-none campaign |
| `papr/clipping.yaml` | active | Single CR hard clipping |
| `papr/clipping_cr_grid.yaml` | active | CR sweep for PAPR vs distortion studies |
| `profiles/development.yaml` | active | Fast debug |
| `profiles/research.yaml` | active | Full block count |
| `profiles/quick_smoke.yaml` | active | Minimal CI / smoke run |
| `profiles/ber_sweep.yaml` | active | BER vs SNR table |

## Phase-2 / preview (not for locked numbers)

| File | Notes |
|------|--------|
| `papr/slm.yaml`, `pts.yaml`, `tone_reservation.yaml`, `ace.yaml` | Config stubs; algorithms raise `NotImplementedError` in Stage-1 |
| `profiles/rayleigh_preview.yaml` | Fading preview; breaks locked AWGN constraints |

---

## How to run

```bash
# Locked baseline via config API / baseline script
python scripts/run_baseline.py --seed 42 --snr 20

# Scenario-oriented runner (when fully wired)
python scripts/run_experiment.py --scenario scenarios/baseline.yaml
python scripts/run_experiment.py --scenario scenarios/papr/clipping.yaml

# PAPR sweep CLI (methods/CR grid; does not require every YAML field)
python scripts/run_papr_sweep.py --methods none,clipping --clip-ratios 1.2,1.5,1.8
```
OR
```

python scripts/run_baseline.py
python scripts/run_experiment.py --scenario scenarios/baseline.yaml
python scripts/run_experiment.py --scenario scenarios/papr/clipping.yaml
python scripts/run_experiment.py --scenario scenarios/profiles/ieee80211a.yaml
python scripts/run_papr_sweep.py --methods none,clipping
```
SLM / PTS / TR scenarios will raise NotImplementedError until Phase-2 algorithms are implemented under papr_methods/.

---

## Authoring rules

1. Keep **locked** scenarios bit-compatible with `configs/baseline.yaml`.
2. Set `scenario.reference: true` only for scientific reference runs.
3. Disable `reference_constraints.require_no_papr_reduction` when using clipping.
4. Always exclude CP from PAPR (`papr.include_cp: false`).
5. Use centralized RNG seeds; never document global `np.random.seed`.
6. Mark Phase-2 files with `status: stub` or `preview`.

---

## Related documentation

- Canonical config: [`../configs/baseline.yaml`](../configs/baseline.yaml)
- Scripts: [`../scripts/README.md`](../scripts/README.md)
- PAPR methods: [`../papr_methods/README.md`](../papr_methods/README.md)
- Examples: [`../examples/README.md`](../examples/README.md)
```

---

این‌ها را commit کن؛ بعد می‌رویم سراغ **`results`**.
