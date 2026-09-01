# References — OFDM-PAPR-LinkSim

This directory contains the scientific and technical reference materials
used to support the development, validation, and future expansion of
**OFDM-PAPR-LinkSim**.

The project is primarily focused on the study and simulation of
**Peak-to-Average Power Ratio (PAPR) reduction in OFDM systems**.

References are organized according to their role in the project:

* **Core Scientific References** — the primary theoretical foundation of
  the current project phase.
* **Supporting Research References** — additional papers that may be used
  to support future experiments, comparisons, or literature review.
* **Future Standards & Implementation References** — standards,
  specifications, and software documentation reserved for later
  development stages.

---

## Directory Structure

```text
references/
├── rahmatallah2013.pdf
├── seungheehan2005.pdf
└── README.md
```

Additional references may be added as the project evolves.

---

# 1. Current Scientific Foundation

The current scientific foundation of **OFDM-PAPR-LinkSim** is deliberately
limited to two major PAPR research references.

These references form the theoretical baseline for the initial development
and experimental methodology of the project.

### Core references

| Year | Reference                                                                                                   | Role                                             |
| ---- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| 2005 | Han & Lee — *An Overview of Peak-to-Average Power Ratio Reduction Techniques for Multicarrier Transmission* | Foundational PAPR-reduction survey               |
| 2013 | Rahmatallah & Mohan — *Peak-To-Average Power Ratio Reduction in OFDM Systems: A Survey and Taxonomy*        | Primary modern taxonomy and evaluation reference |

The two papers complement each other:

* The **2005 paper** provides a foundational overview of the major
  PAPR-reduction families and their fundamental trade-offs.
* The **2013 paper** provides a more systematic taxonomy of PAPR-reduction
  techniques, together with discussion of evaluation criteria,
  implementation complexity, and system-level considerations.

Together, they provide the scientific foundation for the current
PAPR-reduction research direction of this project.

---

# 2. Core Reference — Han & Lee (2005)

## `seungheehan2005.pdf`

### Full citation

> S. H. Han and J. H. Lee,
> "An Overview of Peak-to-Average Power Ratio Reduction Techniques for
> Multicarrier Transmission,"
> *IEEE Wireless Communications*, vol. 12, no. 2, pp. 56–65, Apr. 2005.
> DOI: 10.1109/MWC.2005.1421929.

This paper presents a broad overview of important PAPR-reduction
techniques for multicarrier transmission systems, including OFDM and DMT.

The paper discusses techniques such as:

* Amplitude clipping and filtering
* Coding
* Partial Transmit Sequence (PTS)
* Selected Mapping (SLM)
* Interleaving
* Tone Reservation (TR)
* Tone Injection (TI)
* Active Constellation Extension (ACE)

It also discusses criteria for selecting a suitable PAPR-reduction
technique and provides context for PAPR reduction in systems such as
OFDMA and MIMO-OFDM.

### Role in OFDM-PAPR-LinkSim

This paper serves as the **foundational PAPR-reduction reference** for the
project.

It is particularly important for:

* Establishing the PAPR problem
* Understanding the motivation for PAPR reduction
* Classifying major reduction approaches
* Understanding the fundamental advantages and disadvantages of each
  approach
* Designing the initial PAPR-method roadmap
* Establishing terminology used throughout the project

The techniques discussed in this reference directly correspond to several
methods planned for implementation in the simulator.

---

# 3. Core Reference — Rahmatallah & Mohan (2013)

## `rahmatallah2013.pdf`

### Full citation

> Y. Rahmatallah and S. Mohan,
> "Peak-To-Average Power Ratio Reduction in OFDM Systems: A Survey and
> Taxonomy,"
> *IEEE Communications Surveys & Tutorials*, vol. 15, no. 4,
> pp. 1567–1592, 2013.
> DOI: 10.1109/SURV.2013.021313.00164.

The paper presents a systematic survey and taxonomy of PAPR-reduction
solutions for OFDM systems. It discusses the PAPR problem, its effect on
power-amplifier operation and nonlinear distortion, and organizes
PAPR-reduction approaches into major methodological categories.

### Role in OFDM-PAPR-LinkSim

This paper is the **primary modern research reference** for the project's
PAPR methodology.

It is used to support:

* PAPR definitions and analysis
* Classification of PAPR-reduction techniques
* Performance evaluation criteria
* Complexity considerations
* Comparison between different PAPR-reduction families
* Research-oriented interpretation of simulation results
* Future expansion of the simulator beyond the initial baseline

The taxonomy presented by Rahmatallah and Mohan is particularly useful for
keeping the architecture of the simulator aligned with established
research classifications rather than implementing isolated algorithms
without a consistent theoretical framework.

---

# 4. Relationship Between the Two Core References

The two core papers are not treated as competing references.

They serve different but complementary purposes.

```text
                    OFDM-PAPR-LinkSim
                           │
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       Han & Lee (2005)        Rahmatallah & Mohan (2013)
              │                         │
              │                         │
      Foundational overview       Systematic taxonomy
              │                         │
              │                         │
              └────────────┬────────────┘
                           │
                           ▼
                Current PAPR Framework
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
         Clipping        SLM           PTS
             │
             ├─────────────┐
             ▼             ▼
        Tone Reservation   Future Methods
```

The 2005 reference establishes the broad landscape of PAPR-reduction
techniques, while the 2013 survey provides a more structured framework for
classifying and evaluating those techniques.

Therefore, the current project does **not** define its scientific baseline
from a particular wireless standard or software package.

The baseline is defined from the PAPR research literature itself.

---

# 5. Current Project Scope

The current phase of **OFDM-PAPR-LinkSim** focuses on building a clean,
research-oriented OFDM communication-link simulator in which PAPR
reduction methods can be implemented, tested, and compared under
controlled conditions.

The initial research scope includes:

```text
OFDM Communication Link
        │
        ├── Bit Source
        │
        ├── Channel Coding
        │
        ├── Interleaving
        │
        ├── Digital Modulation
        │
        ├── OFDM Modulation
        │
        ├── PAPR Measurement
        │
        ├── PAPR Reduction
        │      ├── None
        │      ├── Clipping
        │      ├── Clipping + Filtering
        │      ├── SLM
        │      ├── PTS
        │      └── Tone Reservation
        │
        ├── Channel
        │      ├── AWGN
        │      ├── Rayleigh
        │      └── Rician
        │
        ├── Synchronization / Impairments
        │
        ├── Equalization
        │      ├── ZF
        │      └── MMSE
        │
        ├── OFDM Demodulation
        │
        ├── Demodulation
        │
        ├── Decoding
        │
        └── Performance Analysis
               ├── BER
               ├── PAPR / CCDF
               ├── EVM
               ├── PSD
               ├── Constellation
               └── Throughput
```

The simulator is therefore designed around a complete communication-link
perspective rather than treating PAPR as an isolated mathematical
calculation.

---

# 6. PAPR Reduction Methods

The initial implementation roadmap is based on the techniques identified
and discussed in the core references.

## Current / Planned Methods

### 6.1 Baseline — No PAPR Reduction

```text
PAPR method = NONE
```

This is the control condition.

It provides the reference against which every PAPR-reduction method is
evaluated.

No modification is applied to the transmitted OFDM waveform.

---

### 6.2 Clipping

Clipping directly limits the amplitude of the time-domain OFDM signal.

Conceptually:

```text
Original OFDM signal
        │
        ▼
Amplitude clipping
        │
        ▼
Reduced peak amplitude
```

Clipping is important because it represents one of the simplest and most
direct PAPR-reduction approaches.

However, its effect on signal distortion and spectral characteristics must
also be evaluated.

---

### 6.3 Clipping + Filtering

Clipping can introduce undesirable spectral components.

Therefore, filtering can be applied after clipping:

```text
OFDM
 │
 ▼
Clipping
 │
 ▼
Filtering
 │
 ▼
Reduced PAPR waveform
```

This method allows the project to study the trade-off between:

* PAPR reduction
* In-band distortion
* Out-of-band radiation
* Iterative processing complexity

---

### 6.4 Selected Mapping (SLM)

SLM generates multiple alternative representations of the same information
and selects the candidate with the lowest PAPR.

Conceptually:

```text
Input symbols
      │
      ├── Candidate 1 ──► PAPR
      ├── Candidate 2 ──► PAPR
      ├── Candidate 3 ──► PAPR
      ├── Candidate 4 ──► PAPR
      │
      ▼
Select minimum-PAPR candidate
      │
      ▼
Transmit
```

SLM is therefore classified as a multiple-signal / probabilistic approach
rather than a direct waveform-distortion method.

---

### 6.5 Partial Transmit Sequence (PTS)

PTS divides the frequency-domain input into subblocks and optimizes phase
factors to obtain a lower-PAPR time-domain signal.

Conceptually:

```text
Frequency-domain symbols
          │
          ▼
      Subdivision
          │
     ┌────┼────┐
     ▼    ▼    ▼
    X₁    X₂   X₃ ...
     │    │    │
     └────┼────┘
          ▼
   Phase-factor search
          │
          ▼
   Minimum-PAPR signal
```

PTS is particularly relevant for studying the trade-off between PAPR
performance and computational complexity.

---

### 6.6 Tone Reservation (TR)

Tone Reservation reserves selected subcarriers for PAPR-reduction
purposes.

The reserved tones do not carry normal information symbols.

Instead, they are optimized to generate a time-domain correction signal
that reduces peaks.

```text
Frequency-domain subcarriers
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
Data tones   Reserved tones
    │           │
    │           ▼
    │       Optimization
    │           │
    └─────┬─────┘
          ▼
     OFDM waveform
          │
          ▼
     Reduced peaks
```

Tone Reservation is especially useful for the project's later
optimization-oriented experiments.

---

# 7. PAPR Evaluation Philosophy

PAPR reduction will not be evaluated solely by asking:

> "Did the PAPR number decrease?"

A useful PAPR-reduction method must be evaluated as part of a communication
system.

The project therefore considers multiple performance dimensions.

```text
                 PAPR Reduction
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
     PAPR             BER              EVM
       │               │                │
       ▼               ▼                ▼
     CCDF          Reliability       Distortion
       │
       └───────────────┬────────────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
            PSD             Throughput
```

The main evaluation metrics include:

* PAPR
* PAPR CCDF
* BER
* EVM
* PSD
* Constellation quality
* Throughput
* Computational complexity

This approach is consistent with the research-oriented treatment of PAPR
reduction in the core literature, particularly the emphasis on evaluating
trade-offs rather than treating PAPR reduction as a single-objective
problem.

---

# 8. PAPR Measurement

The simulator distinguishes between the OFDM waveform itself and the
method used to reduce its peaks.

The baseline PAPR definition is based on the ratio between the maximum
instantaneous signal power and the average signal power:

```text
              max |x(t)|²
PAPR = --------------------------
             E{|x(t)|²}
```

For numerical simulation, the implementation uses the sampled OFDM
waveform.

The project also supports oversampling so that the discrete-time waveform
provides a better approximation of the continuous-time OFDM signal when
estimating peak behavior.

The PAPR analyzer is therefore treated as an independent component of the
simulation pipeline rather than being embedded inside individual PAPR
methods.

---

# 9. Reproducibility

Scientific reproducibility is a core design requirement.

Experiments should use explicitly controlled random-number generation
where randomness is involved.

This is especially important for:

* Random bit generation
* Channel realization
* SLM phase sequences
* PTS optimization
* Noise generation
* Monte-Carlo experiments

A PAPR-reduction experiment should therefore be reproducible when the same
configuration and random seed are used.

The simulator should avoid hidden or uncontrolled sources of randomness.

---

# 10. Reference-to-Implementation Mapping

The relationship between the literature and implementation is maintained
explicitly.

| Research concept  | Project component                  |
| ----------------- | ---------------------------------- |
| OFDM signal model | `blocks/ofdm_modulator.py`         |
| OFDM demodulation | `blocks/ofdm_demodulator.py`       |
| PAPR measurement  | `blocks/papr.py` / PAPR analyzers  |
| Clipping          | `papr_methods/clipping.py`         |
| SLM               | `papr_methods/slm.py`              |
| PTS               | `papr_methods/pts.py`              |
| Tone Reservation  | `papr_methods/tone_reservation.py` |
| Baseline          | `papr_methods/none.py`             |
| BER evaluation    | `analyzers/ber.py`                 |
| PAPR CCDF         | `analyzers/papr.py`                |
| EVM               | `analyzers/evm.py`                 |
| PSD               | `analyzers/psd.py`                 |
| Constellation     | `analyzers/constellation.py`       |
| Throughput        | `analyzers/throughput.py`          |

This mapping is intended to make the research chain traceable:

```text
Literature
    ↓
Theory
    ↓
Algorithm
    ↓
Implementation
    ↓
Experiment
    ↓
Metric
    ↓
Result
```

---

# 11. Supporting References

Additional papers may be added to this directory as the research scope
expands.

Supporting references can be used for:

* Detailed algorithm derivations
* Complexity analysis
* Alternative PAPR methods
* Channel-specific studies
* OFDMA studies
* MIMO-OFDM studies
* Hardware implementation
* Power-amplifier modeling
* Nonlinear distortion
* Advanced optimization methods
* Comparative literature reviews

Supporting references do not automatically become part of the project's
core scientific baseline.

A reference becomes part of the core baseline only when its role is
explicitly established in the project documentation.

---

# 12. Future Standards & Implementation References

The following categories are intentionally **not part of the current
scientific baseline**.

They are reserved for future development stages.

## 12.1 IEEE 802.11 Family

Future versions of the project may incorporate IEEE wireless standards,
including relevant OFDM/OFDMA specifications.

For example:

```text
Future Research
      │
      └── IEEE 802.11
             ├── 802.11ax
             ├── later amendments
             └── future Wi-Fi studies
```

These standards may become relevant when the project moves from a general
research simulator toward:

* Standards-oriented waveform modeling
* OFDMA experiments
* Wi-Fi-oriented scenarios
* Standard-compliant subcarrier allocation
* Standard-specific PAPR studies
* Real-world waveform constraints

**Important:**

IEEE 802.11 standards are **future implementation references** and do not
define the current Phase-1 scientific baseline.

---

## 12.2 MATLAB / Communications Toolbox

MATLAB and Communications Toolbox documentation may be used in later
stages for:

* Cross-validation
* Algorithm comparison
* Reference implementations
* Educational verification
* MATLAB/Python result comparison
* Reproducing published experiments

However, MATLAB documentation is not considered a scientific foundation
for the current project.

The Python implementation is designed independently and is guided by the
research literature rather than by a proprietary software implementation.

---

# 13. Future Research Direction

The reference library is expected to evolve in stages.

### Phase 1 — Core PAPR Research

```text
Han & Lee (2005)
        +
Rahmatallah & Mohan (2013)
        │
        ▼
Core PAPR simulator
        │
        ├── NONE
        ├── Clipping
        ├── Clipping + Filtering
        ├── SLM
        ├── PTS
        └── Tone Reservation
```

### Phase 2 — Expanded PAPR Research

Possible additions:

* ACE
* Tone Injection
* Coding-based methods
* Companding
* Hybrid techniques
* Optimization-based methods
* Low-complexity algorithms

### Phase 3 — Communication-System Expansion

Possible additions:

* MIMO-OFDM
* OFDMA
* Advanced channel models
* CFO
* Timing offset
* Doppler
* Nonlinear power-amplifier models
* EVM constraints
* Spectral regrowth analysis

### Phase 4 — Standards-Oriented Research

Possible additions:

* IEEE 802.11-based waveform studies
* Wi-Fi 6 / 6E / later generations
* Standard-specific OFDMA allocation
* Standard-specific PAPR constraints
* Hardware-oriented evaluation

### Phase 5 — Cross-Platform Validation

Possible additions:

* MATLAB reference implementations
* MATLAB/Python numerical comparison
* Published-result reproduction
* Hardware-in-the-loop experiments

---

# 14. Adding New References

When adding a new reference:

1. Place the PDF in this directory.
2. Use a short, descriptive filename.
3. Add the reference to the appropriate category.
4. Record its purpose.
5. Add the relevant DOI or bibliographic information when available.
6. Explain which project component or research question it supports.
7. Update this README when the reference changes the research scope.
8. Commit the changes.

Recommended naming style:

```text
author_year_shorttopic.pdf
```

Examples:

```text
rahmatallah2013.pdf
seungheehan2005.pdf
author2020_slm.pdf
author2021_pts.pdf
author2022_tonereservation.pdf
```

Avoid unnecessarily long filenames.

---

# 15. Reference Classification Policy

Every reference should have a clearly defined role.

### Core

A reference that directly defines or supports the current scientific
baseline.

```text
CORE
├── rahmatallah2013.pdf
└── seungheehan2005.pdf
```

### Supporting

A reference used to support a particular experiment, algorithm, or
research discussion.

```text
SUPPORTING
├── additional PAPR papers
├── complexity studies
└── algorithm-specific papers
```

### Future

A standard, software document, or research direction reserved for a later
stage.

```text
FUTURE
├── IEEE standards
├── MATLAB documentation
├── hardware specifications
└── advanced communication-system references
```

This classification prevents the reference directory from becoming an
unstructured collection of PDFs.

---

# 16. Citation Policy

The project should cite the original source whenever a theoretical
concept, algorithm, equation, classification, or experimental methodology
is derived from published literature.

In particular:

* PAPR theory → cite the relevant research reference.
* PAPR-reduction taxonomy → cite Rahmatallah & Mohan.
* Historical overview of PAPR methods → cite Han & Lee.
* Algorithm-specific implementation → cite the corresponding original or
  authoritative publication.
* Standard-specific behavior → cite the applicable IEEE standard.
* MATLAB-specific behavior → cite the applicable MathWorks documentation.

The presence of a PDF in this directory does not automatically imply that
every concept in the project is derived from it.

References should be cited according to their actual contribution.

---

# 17. Research Integrity

OFDM-PAPR-LinkSim is intended as a research and educational simulation
project.

The simulator should distinguish clearly between:

```text
Published theory
       │
       ▼
Implementation
       │
       ▼
Experimental result
       │
       ▼
Research interpretation
```

Simulation results must not be presented as experimentally verified
hardware results unless hardware testing has actually been performed.

Likewise, an algorithm implemented in the simulator should not be
described as "standard-compliant" unless the relevant standard
requirements have explicitly been implemented and verified.

---

# 18. Current Reference Status

| Reference                     | File                  | Status   | Role                                               |
| ----------------------------- | --------------------- | -------- | -------------------------------------------------- |
| Han & Lee (2005)              | `seungheehan2005.pdf` | Active   | Core scientific foundation                         |
| Rahmatallah & Mohan (2013)    | `rahmatallah2013.pdf` | Active   | Core scientific foundation                         |
| IEEE 802.11 references        | Future files          | Reserved | Future standards research                          |
| MATLAB Communications Toolbox | Future files          | Reserved | Future cross-validation / implementation reference |
| Additional PAPR literature    | Future                | Optional | Supporting research                                |

---

# 19. Current Baseline — Final Definition

For the current development stage, the scientific baseline of
**OFDM-PAPR-LinkSim** is defined as:

```text
                    OFDM-PAPR-LinkSim
                           │
                           ▼
                  PAPR Reduction Research
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       Han & Lee (2005)        Rahmatallah & Mohan (2013)
              │                         │
              └────────────┬────────────┘
                           ▼
                  Current Research Base
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
      PAPR Theory      Taxonomy        Evaluation
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                  OFDM-PAPR-LinkSim
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Algorithms     Simulator      Analysis
```

**No IEEE wireless standard or MATLAB toolbox is required to define or
justify the current Phase-1 PAPR baseline.**

IEEE standards, MATLAB documentation, and other implementation-oriented
materials are intentionally reserved for future stages of the project.

This separation keeps the current project scientifically focused on the
PAPR-reduction literature itself while leaving a clean path toward
standards-oriented and cross-platform research in later phases.

---

# 20. Related Documentation

* Project overview: [`../README.md`](../README.md)
* PAPR methods: [`../papr_methods/README.md`](../papr_methods/README.md)
* Scenarios: [`../scenarios/README.md`](../scenarios/README.md)
* Scripts: [`../scripts/README.md`](../scripts/README.md)

---

# 21. License

This directory follows the license and contribution rules of the main
project.

The inclusion of research papers, standards, or documentation in this
directory does not transfer copyright ownership of those materials to the
project.

Original publications remain the property of their respective authors,
publishers, and rights holders.

Users of this repository should obtain and use reference materials in
accordance with the applicable copyright, licensing, and institutional
access requirements.
