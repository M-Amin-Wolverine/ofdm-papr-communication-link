# OFDM-PAPR-LinkSim
### A Modular End-to-End OFDM Communication Link Simulator with PAPR Reduction Techniques and Performance Analysis

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Research](https://img.shields.io/badge/Research-OFDM%20%7C%20PAPR-orange.svg)]()
[![Status](https://img.shields.io/badge/Status-Active%20Development-success.svg)]()
[![Simulation](https://img.shields.io/badge/Simulation-Communication%20Systems-blue.svg)]()

---
## Table of Contents

- [Overview](#overview)
- [Research Motivation](#research-motivation)
- [Project Objectives](#project-objectives)
- [System Architecture](#system-architecture)
- [End-to-End Communication Chain](#end-to-end-communication-chain)
- [OFDM Processing](#ofdm-processing)
- [PAPR Problem](#papr-problem)
- [PAPR Reduction Techniques](#papr-reduction-techniques)
- [Channel Models](#channel-models)
- [Synchronization and Impairments](#synchronization-and-impairments)
- [Equalization](#equalization)
- [Channel Coding](#channel-coding)
- [Performance Metrics](#performance-metrics)
- [Simulation Scenarios](#simulation-scenarios)
- [Parameter Analysis](#parameter-analysis)
- [Power Amplifier Analysis](#power-amplifier-analysis)
- [Link Budget and Coverage Extension](#link-budget-and-coverage-extension)
- [Real-World Application Scenarios](#real-world-application-scenarios)
- [Project Structure](#project-structure)
- [Software Architecture](#software-architecture)
- [Installation](#installation)
- [Requirements](#requirements)
- [Running the Simulator](#running-the-simulator)
- [Example Configuration](#example-configuration)
- [Output and Results](#output-and-results)
- [Reproducibility](#reproducibility)
- [Research Methodology](#research-methodology)
- [Validation Strategy](#validation-strategy)
- [References](#references)
- [Future Work](#future-work)
- [Citation](#citation)
- [License](#license)
- [Author](#author)
---
## Overview

**OFDM-PAPR-LinkSim** is a modular and research-oriented simulation framework for designing, evaluating, and analyzing a complete digital communication link based on **Orthogonal Frequency Division Multiplexing (OFDM)** with a special focus on **Peak-to-Average Power Ratio (PAPR) reduction techniques**.

The project is developed as an advanced academic and engineering platform for investigating the impact of waveform design, channel impairments, coding schemes, equalization methods, and PAPR reduction algorithms on system performance.

Unlike simplified OFDM demonstrations, this framework implements an **end-to-end communication chain**, starting from real data sources and ending with recovered information and comprehensive performance evaluation.

The complete system can process real input data such as:

- Text
- Images
- Audio
- Video
- MPEG-TS
- Arbitrary binary files

The data is converted into a binary stream, protected using error-detection and channel-coding techniques, mapped onto modulation symbols, transmitted using OFDM, passed through configurable channel models, equalized and demodulated at the receiver, decoded, and reconstructed into the original data format.

The framework additionally provides quantitative and visual analysis of:

- BER
- PAPR
- PAPR CCDF
- EVM
- Throughput
- Spectral efficiency
- PSD
- Constellation diagrams
- Time-domain OFDM waveforms
- Computational complexity
- Power-amplifier effects

---

## Research Motivation
OFDM is widely used in modern wireless and broadband communication systems because it provides high spectral efficiency and robustness against frequency-selective multipath channels.

However, one of its fundamental disadvantages is its potentially high **Peak-to-Average Power Ratio**.

High Peak-to-Average Power Ratio (PAPR) is one of the major drawbacks of OFDM systems. Large signal peaks force the Power Amplifier (PA) to operate with significant back-off, reducing power efficiency and degrading overall system performance.

For an OFDM signal

$$\[
x[n] = \frac{1}{N}\sum_{k=0}^{N-1}X_k e^{j2\pi kn/N}
\]$$

multiple independently modulated subcarriers can constructively combine in the time domain and produce large signal peaks.

The PAPR is defined as

$$\[
PAPR =
\frac{\max_n |x[n]|^2}
{\mathbb{E}[|x[n]|^2]}
\]$$

or, in decibels,

$$\[PAPR_{dB}=10\log_{10}\left(\frac{P_{peak}}{P_{average}}\right)\]$$

A high PAPR creates a significant challenge for the RF Power Amplifier.

When the OFDM waveform approaches the nonlinear region of the amplifier, nonlinear distortion can occur, resulting in:

- In-band distortion
- Increased EVM
- Increased BER
- Spectral regrowth
- Adjacent-channel interference
- Reduced power efficiency

Therefore, reducing PAPR while maintaining acceptable BER and spectral performance is an important research problem.

This project investigates:

- PAPR behavior in OFDM systems
- Classical and modern PAPR reduction techniques
- BER and spectral efficiency trade-offs
- Impact of channel impairments
- Effects of Power Amplifier nonlinearity
- Practical communication scenarios inspired by wireless and broadcasting systems

---
## Project Objectives

The project has two major objectives.

### Objective 1 — Complete Communication Link
- [Implement a complete digital communication system](#system-architecture)

### Objective 2 — Complete PAPR Investigation
Investigate and compare different PAPR reduction techniques:
- No PAPR Reduction
- Clipping
- Clipping + Filtering
- Selected Mapping (SLM)
- Partial Transmit Sequence (PTS)
- Tone Reservation (TR)
- Active Constellation Extension (ACE) — optional extension

The techniques are evaluated not only by their PAPR reduction capability but also by their effects on:

- BER
- EVM
- PSD
- Throughput
- Spectral efficiency
- Computational complexity

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
## End-to-End Communication Chain
### 1. Source

The simulator accepts arbitrary digital input data.

Supported source types include:
```
TEXT
IMAGE
AUDIO
VIDEO
MPEG-TS
BINARY
```
Example:
```
input.mp4
    ↓
FFmpeg / MPEG Transport Stream
    ↓
Binary Data
    ↓
Communication System
```

The use of real files makes the simulation closer to an actual communication system rather than a purely random-bit experiment.

## 2. CRC

A Cyclic Redundancy Check is optionally added for error detection.
```
Input Data
     ↓
CRC Encoder
     ↓
Protected Data

At the receiver:

Recovered Data
     ↓
CRC Decoder
     ↓
Error Detection
```
## 3. Channel Coding

Forward Error Correction is used to improve the reliability of the communication link.

Potential coding schemes include:

- Convolutional Coding
- LDPC
- Turbo Coding — optional
- Polar Coding — future extension

The initial baseline can use a convolutional code because it provides a relatively simple and reproducible reference implementation.

## 4. Interleaving

Interleaving is applied after channel coding.
```
Coded Bits
    ↓
Interleaver
    ↓
Interleaved Bits
```
The purpose is to distribute burst errors over different codeword positions, allowing the channel decoder to correct errors more effectively.

5. Digital Modulation

The simulator supports multiple modulation orders.

Current design targets:
```
QPSK
16-QAM
64-QAM
256-QAM
1024-QAM
```
The modulation order affects:

- BER
- Throughput
- Spectral efficiency
- PAPR statistics
- EVM
- Required SNR


## OFDM Processing

The OFDM transmitter performs:
```
QAM Symbols
     ↓
Subcarrier Mapping
     ↓
IFFT
     ↓
Parallel → Serial
     ↓
Cyclic Prefix Insertion
     ↓
Time-Domain OFDM Waveform
```
The receiver performs:
```
Received OFDM Waveform
     ↓
CP Removal
     ↓
Serial → Parallel
     ↓
FFT
     ↓
Subcarrier Extraction
     ↓
QAM Symbols
```

## FFT Size

The simulator is designed to support multiple FFT sizes:
```
N = 64
N = 128
N = 256
N = 512
N = 1024
```

FFT size affects:

- Number of subcarriers
- Subcarrier spacing
- PAPR statistics
- Computational complexity
- Spectral characteristics

The exact baseline value will be selected from a documented communication standard or research reference rather than arbitrarily chosen.

---

## Cyclic Prefix

The simulator supports configurable CP ratios such as:
```
1/4
1/8
1/16
```

Additional values can be investigated when appropriate.

The CP provides robustness against:

- Inter-Symbol Interference (ISI)
- Multipath propagation
- Frequency-selective fading

However, increasing CP length introduces overhead and reduces spectral efficiency.

---

## PAPR Problem

For a discrete OFDM signal (x[n]):

$$[PAPR =\frac{\max |x[n]|^2}{\mathbb{E}[|x[n]|^2]}]$$

The complementary cumulative distribution function (CCDF) is used to statistically evaluate PAPR:

$$[ CCDF(PAPR\_0)=Pr(PAPR>PAPR\_0)]$$

The PAPR CCDF is one of the primary outputs of this project.

Example:

```
Probability
    │
1.0 ┤\
    │ \
    │  \
    │   \
    │    \
    │     \________
    │
    └──────────────────
        PAPR (dB)
```

---

## PAPR Reduction Techniques

### 1. No PAPR Reduction

Baseline reference:

```text
OFDM
 ↓
Channel
```
This configuration is used as the reference against which all PAPR reduction algorithms are compared.

---

## 2. Clipping

Clipping limits the amplitude of the OFDM waveform.

A typical clipping operation is:

$$[x\_c[n] =\begin{cases}x[n], & |x[n]|\leq A\\A e^{j\angle x[n]}, & |x[n]|>A\end{cases}]$$

where (A) is the clipping threshold.

Important parameter:

```text
Clipping Ratio
```

Clipping can significantly reduce PAPR but may introduce:

- In-band distortion
- BER degradation
- Spectral regrowth

---
## 3. Clipping + Filtering

To reduce spectral regrowth caused by clipping:

```text
OFDM
 ↓
Clipping
 ↓
Frequency-Domain Filtering
 ↓
Output
```

This allows investigation of the trade-off between:

```text
PAPR Reduction
       ↕
Spectral Regrowth
       ↕
BER
```
---

## 4. Selected Mapping — SLM

Selected Mapping generates multiple statistically equivalent representations of the same information.

```text
Input Symbols
      │
 ┌────┼────┬────┐
 ▼    ▼    ▼    ▼
Phase Rotation
 │    │    │    │
IFFT IFFT IFFT IFFT
 │    │    │    │
PAPR PAPR PAPR PAPR
 └────┼────┴────┘
      ▼
Lowest-PAPR Candidate
```

The receiver must know which phase sequence was selected.

Therefore, side information is an important practical consideration.

---

## 5. Partial Transmit Sequence — PTS

In PTS, the input frequency-domain symbols are divided into multiple sub-blocks.

```text
Input Symbols
      │
 ┌────┼─────┐
 ▼    ▼     ▼
Subblock 1  2 ... V
 │    │     │
IFFT IFFT  IFFT
 │    │     │
 └────┼─────┘
      ▼
Phase Optimization
      │
      ▼
Minimum PAPR Signal
```

PTS can provide significant PAPR reduction but generally introduces higher computational complexity.

---

## 6. Tone Reservation — TR

Tone Reservation reserves a subset of subcarriers exclusively for PAPR reduction.

```text
Data Subcarriers
       +
Reserved Subcarriers
       ↓
Optimization
       ↓
Reduced-PAPR OFDM Signal
```

The main trade-off is:

```text
PAPR Reduction
       ↕
Data Rate / Spectral Efficiency
```

---

## 7. Active Constellation Extension — ACE

ACE is planned as an optional extension.

It modifies constellation points within allowable regions to reduce signal peaks without directly discarding information.

ACE may be included as an advanced research extension after the classical algorithms have been validated.

---

## Channel Models

The simulator supports multiple channel conditions.

## AWGN

Additive White Gaussian Noise provides the baseline channel.

```text
OFDM
 ↓
AWGN
 ↓
Receiver
```

---

## Rayleigh Fading

Rayleigh fading models multipath environments without a dominant line-of-sight component.

It is particularly useful for investigating mobile wireless environments.

---

## Rician Fading

Rician fading includes a dominant line-of-sight component.

It provides a useful comparison with Rayleigh fading.

---

## Synchronization and Channel Impairments

After the baseline system is validated, additional non-idealities can be introduced.

### Carrier Frequency Offset — CFO

$$[\Delta f \neq 0]$$

CFO can cause:

- Inter-Carrier Interference (ICI)
- Constellation rotation
- BER degradation

---

### Timing Offset

Timing synchronization errors can cause:

- ISI
- ICI
- OFDM orthogonality degradation
- BER increase

---

### Doppler

For a moving receiver:

```text
User Velocity
      ↓
Doppler Shift
      ↓
Time-Varying Channel
      ↓
ICI
      ↓
BER Degradation
```

This allows the simulator to investigate mobile scenarios.

---

## Equalization

The receiver supports different equalization strategies.

### Zero Forcing — ZF

ZF attempts to invert the channel response.

Advantages:

- Simple
- Effective under moderate channel conditions

Disadvantage:

- Noise enhancement can become significant

---

### Minimum Mean Square Error — MMSE

MMSE balances channel inversion and noise enhancement.

It is generally more robust than ZF in noisy environments.

The simulator can compare:

```text
ZF vs MMSE
```

using:

- BER
- EVM
- Constellation
- Throughput

---

## Performance Metrics

The simulator provides multiple quantitative metrics.

### BER

$$[BER =\frac{N\_{bit,error}}{N\_{bit,total}}]$$

Primary plot:

```text
BER vs SNR
```

---

## PAPR

PAPR is evaluated for:

- Original OFDM
- Clipped OFDM
- SLM
- PTS
- Tone Reservation
- ACE

---

## PAPR CCDF

The primary statistical PAPR plot:

```text
CCDF
  │
  │\
  │ \
  │  \
  │   \
  │    \
  │     \____
  └──────────────
       PAPR (dB)
```

The CCDF allows direct comparison of PAPR reduction methods.

---

## EVM

Error Vector Magnitude is used to quantify modulation quality.

It is particularly important when evaluating:

- Clipping
- Power amplifier nonlinearities
- Channel impairments

---

## PSD

Power Spectral Density is used to investigate:

- Spectral regrowth
- Out-of-band emissions
- Effects of clipping
- Power amplifier nonlinearity

---

## Constellation

Constellation diagrams will be generated for different points in the communication chain.

Examples:

```text
Transmitted 16-QAM
        vs
Received 16-QAM
```

This provides a visual representation of channel and nonlinear distortion.

---

## Time-Domain Waveform

The simulator generates:

```text
Original OFDM Waveform
        vs
PAPR-Reduced OFDM Waveform
```

This is particularly important for demonstrating the physical effect of PAPR reduction.

---

## Throughput

Effective throughput will account for system parameters such as:

- Modulation order
- Coding rate
- OFDM symbol duration
- Cyclic-prefix overhead
- Reserved subcarriers
- System overhead

A simplified expression is:

$$[R\_b =\frac{N\_{data} \times \log\_2(M) \times R\_c}{T\_{OFDM}}]$$

where:

- $$(N\_{data})$$ = number of data subcarriers
- $$(M)$$ = modulation order
- $$(R\_c)$$ = coding rate
- $$(T\_{OFDM})$$ = OFDM symbol duration

---

## Simulation Scenarios

The project will use controlled experiments.

### Scenario 1 — Baseline

```text
Modulation : QPSK / 16-QAM
Channel    : AWGN
PAPR       : None
Equalizer  : Ideal / ZF
```

Purpose:

Establish a reference implementation.

---

### Scenario 2 — Clipping

```text
Modulation : 16-QAM
Channel    : Rayleigh
PAPR       : Clipping
Equalizer  : MMSE
```

Purpose:

Evaluate the PAPR/BER trade-off.

---

### Scenario 3 — SLM

```text
Modulation : 16-QAM
Channel    : Rayleigh
PAPR       : SLM
Equalizer  : MMSE
```

Purpose:

Evaluate SLM performance and complexity.

---

### Scenario 4 — PTS

```text
Modulation : 16-QAM
Channel    : Rayleigh
PAPR       : PTS
Equalizer  : MMSE
```

Purpose:

Evaluate PTS PAPR reduction and computational complexity.

---

### Scenario 5 — Tone Reservation

```text
Modulation : 16-QAM
Channel    : Rician
PAPR       : Tone Reservation
Equalizer  : MMSE
```

Purpose:

Study PAPR reduction versus spectral-efficiency overhead.

---

## Parameter Analysis

After validating the baseline system, a controlled parameter sweep will be performed.

---

### FFT Size

```text
64
128
256
512
1024
```

Metrics:

- PAPR
- BER
- Complexity
- Throughput

---

### Modulation Order

```text
QPSK
16-QAM
64-QAM
256-QAM
1024-QAM
```

Metrics:

- BER
- PAPR
- EVM
- Throughput
- Spectral efficiency

---

### Cyclic Prefix

Example configurations:

```text
1/4
1/8
1/16
```

Metrics:

- BER
- Throughput
- Spectral efficiency
- Robustness to multipath

---

# Oversampling Analysis

Oversampling is particularly important for accurate PAPR estimation.

The simulator supports:

```text
L = 1
L = 2
L = 4
L = 8
L = 16
```

Higher oversampling allows the simulator to better capture peaks between discrete Nyquist-rate samples.

Therefore:

```text
Higher Oversampling
        ↓
Better Peak Estimation
        ↓
More Accurate PAPR
```

---

## Channel Comparison

The following channel models can be compared:

```text
AWGN
Rayleigh
Rician
```

Primary evaluation:

```text
BER vs SNR
```

Secondary evaluation:

- EVM
- Constellation
- PAPR behavior
- Throughput

---

### CFO Analysis

The simulator can investigate:

```text
CFO = 0
CFO = Small
CFO = Medium
CFO = Large
```

Expected relationship:

```text
CFO
 ↓
ICI
 ↓
Constellation Distortion
 ↓
BER Increase
```

The interaction between PAPR reduction and CFO can also be investigated.

---

## Timing Offset Analysis

The simulator can compare:

```text
Perfect Synchronization
        vs
Timing Offset
```

Metrics:

- BER
- EVM
- Constellation
- ICI

---

## Doppler and Mobility

A mobile-user scenario can be modeled:

```text
          BTS
           │
           │
           │
          🚗
       Moving UE
```

The receiver velocity introduces Doppler effects.

The simulator can investigate:

```text
Velocity
   ↓
Doppler Frequency
   ↓
Channel Variation
   ↓
ICI
   ↓
BER
```

---

## Handover Extension

Handover is treated as an application-level extension rather than a PAPR algorithm.

Example:

```text
        BTS 1                    BTS 2
          │                        │
          │                        │
          │       🚗 UE            │
          └──────────→─────────────┘
```

Potential metrics:

- Link quality
- BER
- Received SNR
- Doppler
- Channel variation
- Handover interruption

The handover algorithm itself is outside the core PAPR implementation.

---

## Power Amplifier Analysis

One of the most important practical consequences of high PAPR is its interaction with the RF Power Amplifier.

A high-PAPR waveform contains large peaks.

If the amplifier operates close to saturation:

```text
OFDM Peak
    ↓
PA Saturation
    ↓
Nonlinear Distortion
    ↓
EVM ↑
BER ↑
Spectral Regrowth ↑
```

Therefore, the amplifier must operate below its saturation point.

This operating margin is related to **Power Back-Off**.

---

## Power Back-Off

For a high-PAPR waveform:

```text
High PAPR
   ↓
Large Required Back-Off
   ↓
Lower Average Operating Power
   ↓
Lower PA Efficiency
```

Consequently, PAPR reduction can potentially allow the PA to operate closer to its efficient region.

Conceptually:

```text
PAPR ↓
  ↓
Required Back-Off ↓
  ↓
Effective Transmit Power ↑
  ↓
Received SNR ↑
  ↓
BER ↓
```

This provides the engineering connection between the mathematical PAPR problem and practical RF transmitter design.

---

## Nonlinear Power Amplifier Model

An optional nonlinear PA block will be introduced:

```text
OFDM
 ↓
PAPR Reduction
 ↓
Nonlinear PA
 ↓
Channel
 ↓
Receiver
```

Potential PA models include:

- Soft Limiter
- Rapp Model
- Saleh Model

Performance metrics:

- BER
- EVM
- PAPR
- Spectral regrowth
- ACPR
- PA efficiency

---

## Link Budget and Coverage Extension

A further extension can introduce a simplified link-budget model:

```text
Transmit Power
      ↓
Antenna Gain
      ↓
Path Loss
      ↓
Fading
      ↓
Received Power
      ↓
SNR
      ↓
BER
```

Distance can then be varied:

```text
1 km
2 km
5 km
10 km
...
```

This enables investigation of:

```text
Distance ↑
   ↓
Path Loss ↑
   ↓
Received Power ↓
   ↓
SNR ↓
   ↓
BER ↑
```

The additional effect of PAPR-induced PA back-off can then be investigated.

This module is considered an **advanced extension**, not a mandatory component of the core simulator.

---

## Real-World Application Scenarios

The architecture is designed to support realistic communication use cases.

### Broadcasting

Example:

```text
Studio
  ↓
Video Encoding
  ↓
MPEG-TS
  ↓
OFDM Transmitter
  ↓
RF Channel
  ↓
Receiver / Set-Top Box
  ↓
Video Reconstruction
```

---

### Mobile Communications

Example:

```text
Video / Data
    ↓
Base Station
    ↓
OFDM
    ↓
Wireless Channel
    ↓
Moving User Equipment
    ↓
Doppler / Fading
    ↓
Receiver
```

These scenarios provide practical motivation for the simulation parameters and channel models.

---
## Project Philosophy

- Build the complete communication link first.
- Validate the baseline.
- Introduce PAPR reduction.
- Measure the trade-offs.
- Add realistic impairments.
- Connect the results to real RF engineering.

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
| S2       | QPSK       | Rayleigh | None             |
| S3       | 16-QAM     | AWGN     | SLM              |
| S3       | 16-QAM     | Rayleigh | SLM              |
| S4       | 16-QAM     | Rayleigh | PTS              |
| S5       | 16-QAM     | Rician   | Tone Reservation |

### The scenarios can subsequently be expanded to include:

- QPSK
- 64-QAM
- 256-QAM
- Different coding rates
- Different FFT sizes
- Different channel models
- Different equalizers
- Different oversampling factors

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
## Software Architecture

The simulator follows a modular block-based architecture.

Each communication block is designed to have a clearly defined input/output interface.

For example:

```python
bits
  ↓
channel_encoder()
  ↓
coded_bits
```

and:

```python
symbols
  ↓
ofdm_modulate()
  ↓
ofdm_waveform
```

This design allows individual blocks to be replaced without redesigning the entire communication chain.

---

## Configuration Architecture

All major simulation parameters should be controlled from a central configuration system.

Example:

```python
config = {
    "modulation": "16QAM",
    "fft_size": 256,
    "cp_ratio": 1 / 8,
    "oversampling": 4,
    "coding_rate": 0.5,
    "channel": "rayleigh",
    "equalizer": "MMSE",
    "papr_method": "SLM",
    "snr_db": 20,
}
```

This allows reproducible experiments and automated parameter sweeps.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link.git
```

Enter the project:

```bash
cd ofdm-papr-communication-link
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

Activate it on Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Requirements

Expected software environment:

```text
Python >= 3.10
NumPy
SciPy
Matplotlib
Pandas
PyYAML
```

Optional packages may include:

```text
scikit-dsp-comm
commpy
plotly
rich
```

Exact dependencies will be maintained in:

```text
requirements.txt
```

---

## Running the Simulator

Basic execution:

```bash
python main.py
```

Run a specific scenario:

```bash
python main.py --scenario baseline
```

Example:

```bash
python main.py --scenario slm
```

Run a parameter sweep:

```bash
python main.py --sweep
```

Generate results:

```bash
python main.py --scenario clipping --snr 20
```

The exact command-line interface will evolve with the simulator.

---

## Example Configuration

Example baseline configuration:

```python
MODULATION = "16QAM"

FFT_SIZE = 256

CP_RATIO = 1 / 8

OVERSAMPLING = 4

CHANNEL = "AWGN"

EQUALIZER = "ZF"

PAPR_METHOD = "NONE"

SNR_DB = 20

CODING = "CONVOLUTIONAL"

CODING_RATE = 0.5
```

Example SLM configuration:

```python
PAPR_METHOD = "SLM"

SLM_NUM_CANDIDATES = 16
```

Example clipping configuration:

```python
PAPR_METHOD = "CLIPPING"

CLIPPING_RATIO = 2.5
```

---

## Output and Results

Simulation outputs will be stored under:

```text
results/
```

Example:

```text
results/
├── figures/
│   ├── ber_vs_snr.png
│   ├── papr_ccdf.png
│   ├── constellation.png
│   ├── psd.png
│   └── waveform.png
│
├── tables/
│   ├── ber_results.csv
│   ├── papr_results.csv
│   └── throughput_results.csv
│
└── logs/
    └── simulation.log
```

---

## Expected Main Results

The final project will generate at least:

### BER

```text
BER vs SNR
```

### PAPR

```text
PAPR CCDF
```

### Constellation

```text
Transmitted vs Received
```

### Waveform

```text
Original OFDM
vs
PAPR-Reduced OFDM
```

### PSD

```text
Power Spectral Density
```

### Throughput

```text
Effective Bit Rate
```

### EVM

```text
EVM vs SNR
```

---

## Comparative Evaluation

The main research comparison will follow:

```text
                    PAPR
                     │
                     ▼
             ┌──────────────┐
             │ OFDM Signal  │
             └──────┬───────┘
                    │
     ┌──────────────┼──────────────┐
     │       │      │       │      │
     ▼       ▼      ▼       ▼      ▼
    None  Clipping  SLM     PTS     TR
     │       │      │       │      │
     └───────┴──────┴───────┴──────┘
                    │
                    ▼
             Performance
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
       BER         EVM       Throughput
        │           │           │
        └───────────┼───────────┘
                    ▼
                  PSD
```

The objective is not simply to minimize PAPR.

The actual optimization problem is:

```text
PAPR Reduction
        ↕
BER
        ↕
EVM
        ↕
PSD
        ↕
Throughput
        ↕
Complexity
```

A method with the lowest PAPR is not necessarily the best overall method.

---

## Research Methodology

The project follows a controlled experimental methodology.

### Step 1 — Literature Review

Relevant literature and standards are studied to determine:

- OFDM parameters
- FFT size
- CP configuration
- Modulation
- Coding
- Channel model
- PAPR algorithms
- Evaluation metrics

---

### Step 2 — Baseline Implementation

A reference OFDM link is implemented first:

```text
Source
 ↓
Coding
 ↓
Modulation
 ↓
OFDM
 ↓
AWGN
 ↓
Equalization
 ↓
Demodulation
 ↓
Decoding
 ↓
BER
```

No PAPR reduction is applied.

---

### Step 3 — Validation

The baseline is validated against:

- Analytical expectations
- Known OFDM behavior
- Reference literature
- Standardized configurations

---

### Step 4 — PAPR Algorithms

The following techniques are introduced individually:

```text
None
Clipping
Clipping + Filtering
SLM
PTS
Tone Reservation
```

---

### Step 5 — Comparative Evaluation

Each method is evaluated under identical conditions.

Metrics:

```text
PAPR
BER
EVM
PSD
Throughput
Complexity
```

---

### Step 6 — Parameter Sweeps

The following parameters are systematically varied:

```text
FFT Size
Modulation Order
CP Ratio
Oversampling
SNR
Channel Model
Equalizer
PAPR Method
```

---

### Step 7 — Advanced Impairments

After the baseline system is validated:

```text
CFO
Timing Offset
Doppler
Mobility
```

are introduced.

---

### Step 8 — RF Engineering Extension

Finally:

```text
PAPR
 ↓
Power Back-Off
 ↓
Power Amplifier
 ↓
Efficiency
 ↓
Spectral Regrowth
 ↓
BER / EVM
```

can be investigated.

---

## Validation Strategy

A major design principle of this project is:

> **Do not add advanced features before validating the fundamental communication chain.**

The implementation will therefore follow:

```text
Baseline
   ↓
Unit Tests
   ↓
End-to-End Test
   ↓
Reference Validation
   ↓
PAPR Algorithms
   ↓
Channel Impairments
   ↓
PA Model
   ↓
Link Budget
```

This prevents errors in one block from being incorrectly attributed to another block.

---

## Reproducibility

Experiments should be reproducible.

Therefore the simulator will provide:

- Configurable random seeds
- Explicit simulation parameters
- Stored experiment configurations
- Versioned results
- CSV result files
- Automatically generated figures
- Scenario identifiers

Example:

```python
RANDOM_SEED = 42
```

Every published result should record:

```text
Simulation ID
FFT Size
CP
Modulation
Coding
Channel
SNR
PAPR Method
Oversampling
Random Seed
```

---

## Scientific Design Principles

The project follows several principles:

### 1. Modularity

Every communication block should be independently replaceable.

### 2. Reproducibility

Experiments should be repeatable under identical configurations.

### 3. Fair Comparison

PAPR reduction methods must be evaluated under identical channel and SNR conditions.

### 4. Standard-Based Parameters

Baseline parameters should be justified using recognized standards or peer-reviewed literature.

### 5. Quantitative Evaluation

Claims should be supported by measurable metrics.

### 6. End-to-End Validation

The simulator must be capable of recovering real input data.

---

## References

The project is based on established OFDM and PAPR literature.

### Fundamental PAPR Reference

S. H. Han and J. H. Lee,

> "An Overview of Peak-to-Average Power Ratio Reduction Techniques for Multicarrier Transmission"

IEEE Wireless Communications, 2005.

This work provides a comprehensive classification of PAPR reduction approaches.

---

### PAPR Survey

Y. Rahmatallah and S. Mohan,

> "Peak-to-Average Power Ratio Reduction in OFDM Systems: A Survey and Taxonomy"

IEEE Communications Surveys & Tutorials, 2013.

---

### Selected Mapping

R. W. Bäuml, R. F. H. Fischer, and J. B. Huber,

> "Reducing the Peak-to-Average Power Ratio of Multicarrier Modulation by Selected Mapping"

Electronics Letters, 1996.

---

### Partial Transmit Sequence

S. H. Müller and J. B. Huber,

> "OFDM with Reduced Peak-to-Average Power Ratio by Optimum Combination of Partial Transmit Sequences"

Electronics Letters, 1997.

---

### Clipping and Filtering

J. Armstrong,

> "Peak-to-Average Power Reduction for OFDM by Repeated Clipping and Frequency Domain Filtering"

Electronics Letters, 2002.

---

### PAPR Reduction Theory

J. Tellado,

> "Peak to Average Power Reduction for Multicarrier Modulation"

Ph.D. dissertation, Stanford University, 1999.

---

### Standards

The project will use relevant communication standards for parameter selection and validation, including:

- IEEE 802.11 family
- 3GPP LTE
- 3GPP 5G NR where applicable

The exact standard used for each baseline experiment will be explicitly documented in the experiment configuration and references.

---

## Academic Deliverables

The project is designed to produce:

### 1. Source Code

Complete modular simulation implementation.

### 2. Simulation Results

Including:

- BER curves
- PAPR CCDF
- Constellation diagrams
- PSD
- Waveforms
- EVM
- Throughput

### 3. Technical Report

The report will cover:

```text
1. Introduction
2. OFDM Fundamentals
3. PAPR Problem
4. PAPR Reduction Techniques
5. Communication Link Design
6. Simulation Methodology
7. Experimental Results
8. Parameter Analysis
9. Advanced Analysis
10. Conclusion
```

### 4. References

Scientific papers, books, and standards used for parameter selection and theoretical foundations.

### 5. Demonstration Video

A short technical demonstration showing:

- System architecture
- Source input
- Simulation configuration
- Code execution
- OFDM waveform
- PAPR reduction
- Channel effects
- BER results
- Final recovered data

---
## Graphical User Interface

After validating the simulation engine, a graphical interface can be developed.

Concept:

```text
┌─────────────────────────────────────────────┐
│              OFDM-PAPR-LinkSim              │
├─────────────────────────────────────────────┤
│ Modulation       [ 16-QAM ▼ ]               │
│ FFT Size         [ 256 ]                    │
│ CP Ratio         [ 1/8 ▼ ]                  │
│ Channel          [ Rayleigh ▼ ]             │
│ Equalizer        [ MMSE ▼ ]                 │
│ PAPR Method      [ SLM ▼ ]                  │
│ Oversampling     [ 4 ]                      │
│ SNR              [ 20 dB ]                  │
│                                             │
│          [ RUN SIMULATION ]                 │
├─────────────────────────────────────────────┤
│ BER       │ PAPR      │ Throughput          │
│ EVM       │ PSD       │ Efficiency          │
├─────────────────────────────────────────────┤
│                                             │
│          Waveform / Constellation           │
│                                             │
├─────────────────────────────────────────────┤
│                                             │
│             PAPR CCDF / PSD                 │
│                                             │
└─────────────────────────────────────────────┘
```

The GUI is intentionally considered a **second-stage component**.

The simulation engine must be validated before GUI development.

---
## Future Work

The current implementation provides a modular foundation for evaluating and comparing PAPR reduction techniques in OFDM-based communication systems. Several extensions can further improve the realism, adaptability, computational efficiency, and practical relevance of the framework.

### 1. Advanced PAPR Reduction Techniques

Future development can extend the implemented PAPR reduction framework with additional techniques and hybrid approaches, including:

* Active Constellation Extension (ACE)
* Companding-based PAPR reduction
* Hybrid PAPR reduction algorithms
* Adaptive PAPR reduction
* Multi-stage and joint PAPR reduction schemes
* Optimization-based PAPR minimization
* Machine-learning-based PAPR optimization
* Deep-learning-based waveform optimization
* Reinforcement-learning-based parameter selection

These approaches could enable the system to dynamically select or optimize PAPR reduction parameters according to the characteristics of the transmitted OFDM signal.

### 2. Realistic Wireless Channel and Synchronization Models

The simulation environment can be extended toward more realistic wireless communication scenarios by incorporating:

* Doppler and mobility models
* Carrier Frequency Offset (CFO)
* Sampling and timing offsets
* Phase noise
* Frequency-selective fading
* Time-varying multipath channels
* More advanced channel estimation and equalization
* Link-budget analysis
* Coverage analysis
* LTE/5G NR-inspired channel and system scenarios

These extensions would allow the impact of PAPR reduction techniques to be evaluated under practical synchronization, mobility, and propagation impairments.

### 3. Nonlinear RF and Power Amplifier Modeling

Since PAPR is directly related to the operating efficiency and nonlinear distortion of RF power amplifiers, future versions can incorporate realistic amplifier models, such as:

* Nonlinear Power Amplifier (PA) models
* AM/AM and AM/PM characteristics
* Memoryless and memory-based PA models
* Output Back-Off (OBO) analysis
* Error Vector Magnitude (EVM) evaluation
* Adjacent Channel Leakage Ratio (ACLR) analysis
* Spectral regrowth analysis
* Joint PAPR–PA efficiency optimization

This would enable evaluation of the practical trade-off between PAPR reduction, amplifier efficiency, signal distortion, and spectral performance.

### 4. Machine Learning and Intelligent Optimization

Machine learning can be introduced as an adaptive optimization layer capable of learning suitable PAPR reduction parameters from the transmitted signal characteristics.

Potential directions include:

* Supervised learning for PAPR prediction
* Reinforcement learning for adaptive parameter selection
* Deep-learning-based waveform optimization
* Neural-network-based PAPR prediction
* Intelligent selection of PAPR reduction algorithms
* Online adaptation based on channel and signal conditions
* Joint optimization of PAPR, BER, EVM, and computational complexity

Such approaches could transform the framework from a fixed-parameter simulator into an adaptive and intelligent PAPR optimization platform.

### 5. Computational Acceleration and Real-Time Processing

For large-scale experiments and real-time applications, computational performance can be improved through:

* GPU acceleration
* Parallel signal processing
* Batch-based simulation
* Vectorized implementations
* Real-time OFDM processing
* Hardware acceleration
* Computational complexity profiling

GPU and parallel implementations would be particularly useful for large Monte Carlo simulations, deep-learning-based optimization, and high-dimensional parameter sweeps.

### 6. Multimedia and End-to-End Communication

The current signal-level simulation can be extended toward complete end-to-end communication experiments by supporting:

* Real multimedia file transmission
* Audio and video transmission over the OFDM chain
* File-based source generation
* End-to-end BER and throughput evaluation
* Quality-of-Service (QoS) analysis
* Multimedia quality assessment
* Adaptive transmission according to application requirements

This would bridge the gap between theoretical waveform evaluation and application-level communication experiments.

### 7. Software-Defined Radio and Hardware Validation

To evaluate the proposed algorithms beyond simulation, future work can integrate the framework with Software-Defined Radio (SDR) platforms.

Possible extensions include:

* SDR-based OFDM transmission and reception
* Real-world RF experiments
* Hardware-in-the-loop (HIL) testing
* Over-the-air (OTA) experiments
* Real-time PAPR measurement
* Hardware-based nonlinear PA evaluation
* Experimental validation of simulated results

This stage would provide an important transition from numerical simulation toward practical wireless communication systems.

### 8. Graphical Experiment and Analysis Environment

A GUI-based dashboard can be developed to simplify experiment configuration, visualization, and comparative analysis.

Potential GUI capabilities include:

* Interactive OFDM parameter configuration
* Selection of PAPR reduction algorithms
* Real-time waveform visualization
* Constellation diagrams
* PAPR Complementary Cumulative Distribution Function (CCDF) plots
* BER and EVM visualization
* Spectral analysis
* Power amplifier performance visualization
* Automated algorithm comparison
* Experiment logging and result export
* Reproducible experiment configuration

### Long-Term Research Direction

The long-term objective is to evolve the framework from a conventional OFDM simulation environment into a **comprehensive, adaptive, and hardware-aware PAPR optimization platform**. The integration of advanced PAPR reduction algorithms, realistic RF impairments, nonlinear power amplifier models, machine learning, GPU acceleration, multimedia transmission, and SDR-based validation can provide a complete research environment for investigating PAPR reduction from the waveform level to the physical hardware level.


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
  title = {OFDM-PAPR-LinkSim: End-to-End OFDM Communication Link Simulator with PAPR Reduction},
  year = {2026},
  description = {Modular End-to-End OFDM Communication Link Simulator with PAPR Reduction Techniques},
  url = {https://github.com/M-Amin-Wolverine/ofdm-papr-linksim},
  license      = {MIT}      
}
```

---

## License

This project is released under the MIT License.

---

## Project Status

### Current development stages:

- [x] Literature Review
- [x] Standard Selection
- [x] Parameter Definition
- [x] Project Skeleton
- [ ] Source Module
- [ ] CRC
- [ ] Channel Coding
- [ ] Interleaver
- [ ] Modulation
- [ ] OFDM Modulator
- [ ] Baseline Channel
- [ ] Equalizer
- [ ] OFDM Demodulator
- [ ] Channel Decoder
- [ ] End-to-End Validation
- [ ] PAPR Measurement
- [ ] Clipping
- [ ] SLM
- [ ] PTS
- [ ] Tone Reservation
- [ ] BER Analyzer
- [ ] CCDF Analyzer
- [ ] EVM Analyzer
- [ ] PSD Analyzer
- [ ] Throughput Analyzer
- [ ] Parameter Sweeps
- [ ] CFO
- [ ] Timing Offset
- [ ] Doppler
- [ ] Power Amplifier
- [ ] Link Budget
- [ ] GUI
- [ ] Final Report

----
## Acknowledgment

This project was developed as an academic communication-system simulation project with emphasis on OFDM waveform generation, PAPR reduction, channel modeling, and end-to-end link performance evaluation.

The theoretical foundations and parameter-selection methodology are based on established literature, communication standards, and peer-reviewed research.
----

## Contribution

### Contributions are welcome for:

- New PAPR reduction algorithms
- Channel models
- Equalization techniques
- Modulation schemes
- Visualization tools
- Optimization methods
- Testing
- Documentation

**Before submitting major changes, please open an issue describing the proposed modification.**

## Disclaimer

### This project is intended primarily for:

* Academic research
* Educational purposes
* Communication-system simulation
* Algorithm comparison
* Reproducible experimentation

**Simulation results should not automatically be interpreted as measurements of a physical RF system.**

Real-world implementations require consideration of hardware limitations, RF impairments, regulatory constraints, synchronization mechanisms, antenna characteristics, amplifier behavior, and measurement uncertainty.

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
* 5G / 6G Systems
* Communication-System Simulation

---

*"Engineering communication systems by combining theory, simulation, and practical analysis."*

