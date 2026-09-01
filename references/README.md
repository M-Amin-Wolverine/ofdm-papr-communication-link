# References — OFDM-PAPR-LinkSim

**All reference materials** (papers, IEEE standards, MATLAB® toolboxes, and historical OFDM/PAPR literature)  
live under this folder.

```text
references/
├── rahmatallah2013.pdf                # Peak-To-Average Power Ratio Reduction in OFDM
├── seungheehan2005.pdf                # OVERVIEW OF PEAK-TO-AVERAGE POWER RATIO REDUCTION
└── README.md                          # this file
```

---

## How to add new references

1. Drop new PDF / article / book PDF here (keep filename short and descriptive).
2. Update the table of contents (TOC) below if needed.
3. Commit once.

---

## Table of Contents & Purpose

### 1. IEEE 802.11ax (2021)
**File:** `IEEE_802_11ax.pdf`

**Purpose:**  
Official IEEE Standard defining Orthogonal Frequency-Division Multiple Access (OFDMA) for Wi-Fi 6E (6 GHz).  
Covers:
- Subcarrier mapping in OFDM/OFDMA
- PAPR in 802.11ax waveforms
- Clipping and tone reservation techniques in the standard

**Key sections for this project:**
- 16.3.11 OFDM transmission
- 16.3.12 PAPR measurement
- Clipping and Tone Reservation clauses

### 2. MATLAB Communications Toolbox
**File:** `MATLAB_PAPR_toolbox.pdf`

**Purpose:**  
Official MATLAB documentation for `OFDMToolbox` and `comm.PSKModulator` / `comm.OFDMTx` blocks.

**Key sections for this project:**
- `comm.OFDMTx` / `comm.OFDMRx` PAPR estimation
- `comm.OFDMToolbox` (legacy) clipping and SLM examples

---

## How to use these references

| Use case                    | Where to find it |
|-----------------------------|------------------|
| Official Wi-Fi 6E / 802.11ax spec | `IEEE_802_11ax.pdf` |
| MATLAB simulation examples  | `MATLAB_PAPR_toolbox.pdf` |

All references are provided for **academic / research use only** (fair use).  
Please cite the original source in your papers and presentations.

---

## Design principle of this project

**This project is built on two foundational papers:**

1. **IEEE 802.11ax-2021** — Defines the baseline OFDM/OFDMA waveform structure, subcarrier allocation, PAPR measurement rules, and reduction techniques (clipping, tone reservation, SLM, PTS) used in modern Wi-Fi systems.
2. **MATLAB Communications Toolbox documentation** — Provides the reference implementation of OFDM modulation, PAPR estimation, and reduction algorithms (hard/soft clipping, SLM, PTS, ACE).

All other references listed in the full `references/` folder (Rappaport textbook, classic OFDM-PAPR surveys, etc.) were added later to support the research narrative and future experiments. The **core scientific baseline** of this project is **strictly defined by the two documents above**.

---

## Next steps

1. Drop new reference PDFs here if needed.
2. Update this README with any new papers.
3. Commit once.

---

## Related documentation

- Project overview: [`../README.md`](../README.md)
- PAPR methods: [`../papr_methods/README.md`](../papr_methods/README.md)
- Scripts: [`../scripts/README.md`](../scripts/README.md)

---

## License

Same as the main project (see repository `LICENSE`).

**حالا پوشه `references` کامل شد.**  
بگو **«برو scenarios»** تا همین الان فایل `scenarios/README.md` را کامل و حرفه‌ای بنویسم (با جزئیات کامل برای baseline.yaml و ساختار سناریوها).
