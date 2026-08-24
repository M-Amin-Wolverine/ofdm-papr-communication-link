# OFDM-PAPR-LinkSim
### A Modular End-to-End OFDM Communication Link Simulator with PAPR Reduction Techniques and Performance Analysis

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Research](https://img.shields.io/badge/Research-OFDM%20%7C%20PAPR-orange.svg)]()
[![Status](https://img.shields.io/badge/Status-Active%20Development-success.svg)]()

---

## Overview

**OFDM-PAPR-LinkSim** is a modular and research-oriented simulation framework for designing, evaluating, and analyzing a complete digital communication link based on **Orthogonal Frequency Division Multiplexing (OFDM)** with a special focus on **Peak-to-Average Power Ratio (PAPR) reduction techniques**.

The project is developed as an advanced academic and engineering platform for investigating the impact of waveform design, channel impairments, coding schemes, equalization methods, and PAPR reduction algorithms on system performance.

Unlike simplified OFDM demonstrations, this framework implements an **end-to-end communication chain**, starting from real data sources and ending with recovered information and comprehensive performance evaluation.

---

## Research Motivation

High Peak-to-Average Power Ratio (PAPR) is one of the major drawbacks of OFDM systems. Large signal peaks force the Power Amplifier (PA) to operate with significant back-off, reducing power efficiency and degrading overall system performance.

This project investigates:

- PAPR behavior in OFDM systems
- Classical and modern PAPR reduction techniques
- BER and spectral efficiency trade-offs
- Impact of channel impairments
- Effects of Power Amplifier nonlinearity
- Practical communication scenarios inspired by wireless and broadcasting systems

---

## System Architecture

```text
Input File / Data Source
        │
        ▼
Source Generator
        │
        ▼
CRC Encoder
        │
        ▼
Channel Coding
        │
        ▼
Interleaver
        │
        ▼
QPSK / QAM Mapper
        │
        ▼
OFDM Modulator
(IFFT + Cyclic Prefix)
        │
        ▼
PAPR Reduction
        │
        ▼
Power Amplifier (Optional)
        │
        ▼
Channel
(AWGN / Rayleigh / Rician)
        │
        ▼
Synchronization
(Optional)
        │
        ▼
Equalizer
(ZF / MMSE)
        │
        ▼
OFDM Demodulator
        │
        ▼
Channel Decoder
        │
        ▼
CRC Check
        │
        ▼
Recovered Data
        │
        ▼
Performance Analysis
````

---

## Implemented Modules

### Core Communication Blocks

* Source Generator
* CRC Encoder / Decoder
* Channel Coding
* Interleaver
* Modulation / Demodulation
* OFDM Modulation / Demodulation
* Channel Models
* Equalization
* Synchronization
* Output Reconstruction

---

## PAPR Reduction Techniques

### Baseline

* No PAPR Reduction

### Classical Techniques

* Clipping
* Clipping + Filtering
* Selected Mapping (SLM)
* Partial Transmit Sequence (PTS)
* Tone Reservation (TR)

### Future Extensions

* Active Constellation Extension (ACE)
* Companding
* Machine Learning Based PAPR Reduction

---

## Channel Models

* AWGN
* Rayleigh Fading
* Rician Fading

Future:

* Doppler
* Time-Varying Channels
* Mobility Models

---

## Equalization Methods

* Zero Forcing (ZF)
* Minimum Mean Square Error (MMSE)

---

## Performance Metrics

### Communication Metrics

* Bit Error Rate (BER)
* Throughput
* Spectral Efficiency
* EVM

### OFDM Metrics

* PAPR
* CCDF of PAPR

### Signal Analysis

* Constellation Diagram
* PSD
* Time-Domain Waveform

### Complexity Metrics

* Processing Time
* Algorithm Complexity

---

## Simulation Scenarios

| Scenario | Modulation | Channel  | PAPR Method      |
| -------- | ---------- | -------- | ---------------- |
| S1       | QPSK       | AWGN     | None             |
| S2       | QPSK       | Rayleigh | Clipping         |
| S3       | 16-QAM     | Rayleigh | SLM              |
| S4       | 16-QAM     | Rayleigh | PTS              |
| S5       | 16-QAM     | Rician   | Tone Reservation |

---

## Standards and References

Simulation parameters are inspired by:

* IEEE 802.11 OFDM
* LTE / 4G (3GPP TS 36.211)
* 5G NR Concepts
* Classical OFDM Literature

---

## Project Structure

```text
ofdm-papr-linksim/
│
├── main.py
├── config.py
│
├── blocks/
│   ├── source.py
│   ├── crc.py
│   ├── channel_coding.py
│   ├── interleaver.py
│   ├── modulation.py
│   ├── ofdm_modulator.py
│   ├── papr.py
│   ├── channel.py
│   ├── synchronization.py
│   ├── equalizer.py
│   ├── ofdm_demodulator.py
│   ├── channel_decoder.py
│   └── output.py
│
├── papr_methods/
│   ├── none.py
│   ├── clipping.py
│   ├── slm.py
│   ├── pts.py
│   └── tone_reservation.py
│
├── analyzers/
│   ├── ber.py
│   ├── papr.py
│   ├── evm.py
│   ├── psd.py
│   ├── constellation.py
│   └── throughput.py
│
├── scenarios/
├── results/
├── references/
├── docs/
└── README.md
```

---

## Installation

```bash
git clone https://github.com/yourusername/ofdm-papr-linksim.git

cd ofdm-papr-linksim

pip install -r requirements.txt
```

---

## Running a Simulation

```bash
python main.py
```

Example:

```python
modulation = "16QAM"
fft_size = 256
cp_ratio = 1/8
channel = "rayleigh"
papr_method = "SLM"
snr_db = 20
```

---

## Planned Future Work

* GUI Dashboard
* Real Multimedia File Transmission
* Power Amplifier Models
* Doppler Effects
* CFO and Timing Offset
* Link Budget Analysis
* GPU Acceleration
* Machine Learning Based Optimization

---

## Academic References

### Surveys

Han, S. H., & Lee, J. H. (2005).
*An Overview of Peak-to-Average Power Ratio Reduction Techniques for Multicarrier Transmission.*

Rahmatallah, Y., & Mohan, S. (2013).
*Peak-to-Average Power Ratio Reduction in OFDM Systems: A Survey and Taxonomy.*

### Books

Tellado, J. (2000).
*Multicarrier Modulation with Low PAR.*

---

## Citation

If you use this project in academic work:

```bibtex
@software{ofdm_papr_linksim,
  author = {Mohammad Amin Khodadadi},
  title = {OFDM-PAPR-LinkSim},
  year = {2026},
  description = {Modular End-to-End OFDM Communication Link Simulator with PAPR Reduction Techniques},
  url = {https://github.com/yourusername/ofdm-papr-linksim}
}
```

---

## License

This project is released under the MIT License.

---

## Author

**Mohammad Amin Khodadadi**
M.Sc. Student in Telecommunication Systems Engineering

Research Interests:

* OFDM
* PAPR Reduction
* Wireless Communications
* AI-Native 6G
* Digital Communication Systems
* Signal Processing

---

*"Engineering communication systems by combining theory, simulation, and practical analysis."*

```

For GitHub, I would also recommend:

- **Repository Name:** `ofdm-papr-linksim`
- **Visibility:** Public
- **License:** MIT
- **Topics/Tags:**
```

ofdm
papr
wireless-communications
digital-communications
signal-processing
python
lte
5g
ber
qam
research
simulation

```
- Additional files:
```

LICENSE
.gitignore
requirements.txt
docs/
references/
examples/
CITATION.cff
CONTRIBUTING.md
CHANGELOG.md

```
```
