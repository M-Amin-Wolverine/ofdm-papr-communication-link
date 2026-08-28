# Changelog

All notable changes to **OFDM-PAPR-LinkSim** are documented in this file.

**OFDM-PAPR-LinkSim** is a modular, reproducible, end-to-end OFDM communication-link simulation framework designed for the investigation, implementation, and comparative evaluation of Peak-to-Average Power Ratio (PAPR) reduction techniques and their impact on communication-system performance.

The format of this changelog is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

# [Unreleased]

The `Unreleased` section tracks functionality that is planned, under development, experimentally evaluated, or not yet included in a stable release.

## Planned

### Communication System Core

* Implementation of the baseline end-to-end OFDM transmitter and receiver.
* Configurable binary source and random bit generation.
* Optional deterministic random-seed control for reproducible experiments.
* CRC generation and verification.
* Configurable channel coding framework.
* Interleaving and de-interleaving support.
* Digital modulation and demodulation.
* Support for:

  * BPSK
  * QPSK
  * 16-QAM
  * 64-QAM
  * 256-QAM
  * Higher-order QAM where applicable.
* Configurable OFDM symbol generation.
* IFFT-based OFDM modulation.
* FFT-based OFDM demodulation.
* Cyclic-prefix insertion and removal.
* Configurable subcarrier allocation.
* Data, pilot, guard-band, and DC-subcarrier mapping.
* Configurable number of active subcarriers.

### OFDM Parameterization

* Configurable FFT size.
* Configurable number of occupied subcarriers.
* Configurable cyclic-prefix length.
* Configurable oversampling factor.
* Configurable modulation order.
* Configurable number of OFDM symbols per simulation.
* Configurable sampling frequency.
* Configurable subcarrier spacing.
* Configurable symbol duration.
* Configurable pilot structure.
* Configurable guard-band allocation.
* Configurable transmit-power normalization.
* Standardized parameter profiles for controlled experiments.

### PAPR Analysis

* Peak-to-Average Power Ratio measurement.
* Instantaneous-power analysis.
* Peak-power detection.
* Average-power estimation.
* PAPR statistical characterization.
* PAPR distribution analysis.
* Complementary Cumulative Distribution Function (CCDF) generation.
* Configurable CCDF probability resolution.
* PAPR percentile extraction.
* Statistical comparison between baseline and PAPR-reduced signals.
* Peak-power reduction analysis.
* Average-power preservation analysis.

### PAPR Reduction Techniques

A modular PAPR-reduction interface will support interchangeable algorithms without modifying the remainder of the communication chain.

Planned techniques include:

* Clipping.
* Clipping and Filtering.
* Selected Mapping (SLM).
* Partial Transmit Sequence (PTS).
* Tone Reservation (TR).
* Tone Injection (TI).
* Active Constellation Extension (ACE).
* Companding-based methods.
* Hybrid PAPR-reduction approaches.
* Configurable algorithm-specific optimization parameters.

### PAPR Reduction Evaluation

Each PAPR-reduction method will be evaluated not only according to PAPR reduction, but also according to its effect on communication performance.

Planned evaluation dimensions include:

* PAPR reduction in dB.
* CCDF displacement.
* BER degradation or improvement.
* EVM degradation.
* Out-of-band radiation.
* Spectral regrowth.
* PSD variation.
* In-band distortion.
* Constellation distortion.
* Required computational complexity.
* Runtime.
* Memory consumption.
* Number of candidate waveforms.
* Iterative optimization cost.
* Peak-power reduction versus computational complexity trade-off.

### Channel Models

#### AWGN

* Additive White Gaussian Noise channel.
* Configurable SNR range.
* Eb/N0-based simulation.
* Es/N0-based simulation.
* Reproducible noise generation.

#### Frequency-Selective Fading

* Rayleigh fading.
* Rician fading.
* Configurable multipath profiles.
* Configurable path gains.
* Configurable path delays.
* Normalized and physical channel models.

#### Time-Varying Channels

* Doppler frequency modeling.
* Time-varying fading.
* Mobility-aware channel variation.
* Configurable maximum Doppler frequency.
* Configurable channel coherence characteristics.

### Synchronization Impairments

Planned synchronization impairment models include:

* Carrier Frequency Offset (CFO).
* Sampling Frequency Offset (SFO).
* Symbol timing offset.
* Phase offset.
* Phase noise.
* Timing drift.
* Combined synchronization impairments.

### Receiver Processing

* OFDM synchronization framework.
* Cyclic-prefix removal.
* FFT demodulation.
* Pilot-based channel estimation.
* Frequency-domain equalization.
* Zero-Forcing (ZF) equalization.
* Minimum Mean Square Error (MMSE) equalization.
* Symbol demapping.
* De-interleaving.
* Channel decoding.
* CRC verification.
* Bit-error calculation.

---

## Performance Metrics

The simulator will provide a unified evaluation framework for communication-system and waveform-quality metrics.

### PAPR Metrics

* Maximum PAPR.
* Mean PAPR.
* Median PAPR.
* PAPR percentiles.
* CCDF.
* PAPR reduction in dB.

### Communication Metrics

* Bit Error Rate (BER).
* Symbol Error Rate (SER).
* Error Vector Magnitude (EVM).
* Throughput.
* Spectral efficiency.
* Effective data rate.

### Spectral Metrics

* Power Spectral Density (PSD).
* Out-of-band emissions.
* Adjacent-channel leakage where applicable.
* Spectral regrowth.
* In-band distortion.

### Signal-Domain Metrics

* Peak amplitude.
* RMS amplitude.
* Crest factor.
* Peak-to-average power statistics.
* Time-domain waveform characteristics.
* Constellation distribution.

### Computational Metrics

* Execution time.
* Memory consumption.
* Algorithmic complexity.
* Number of optimization iterations.
* Number of generated candidate signals.
* Computational cost per OFDM symbol.

---

# Reproducibility

Reproducibility is a core design objective of the project.

Planned reproducibility mechanisms include:

* Explicit simulation configurations.
* YAML-based experiment configuration.
* Command-line configuration.
* Deterministic random seeds.
* Versioned simulation scenarios.
* Explicit parameter logging.
* Experiment metadata recording.
* Automatic storage of simulation parameters alongside results.
* Standardized output formats.
* Machine-readable experiment results.
* Reproducible figure generation.
* Version-controlled reference configurations.

A simulation result should be traceable to:

1. The software version.
2. The simulation scenario.
3. The OFDM parameters.
4. The channel parameters.
5. The PAPR-reduction parameters.
6. The random seed.
7. The evaluation configuration.

---

# Standardized Simulation Scenarios

A scenario-based architecture will be introduced to prevent uncontrolled parameter changes between experiments.

Planned scenario categories include:

* Baseline OFDM.
* AWGN baseline.
* Rayleigh fading.
* Rician fading.
* High-order QAM.
* High-PAPR stress scenarios.
* Oversampled OFDM.
* CFO-impaired OFDM.
* Doppler-impaired OFDM.
* PAPR-reduction comparison scenarios.
* Computational-complexity benchmarking scenarios.

Each scenario will define a controlled set of parameters and evaluation conditions.

---

# Experimental Framework

A structured experiment layer is planned for systematic research evaluation.

Planned capabilities include:

* Batch simulation.
* Parameter sweeps.
* SNR sweeps.
* Modulation-order sweeps.
* FFT-size sweeps.
* CP-length sweeps.
* Oversampling-factor sweeps.
* PAPR-algorithm parameter sweeps.
* Channel-condition sweeps.
* Automated result aggregation.
* Automated statistical analysis.
* Comparative algorithm benchmarking.

---

# Result Management

Simulation outputs will be organized separately from source code.

Planned result types include:

* CSV datasets.
* JSON experiment metadata.
* NumPy arrays.
* PAPR CCDF plots.
* BER curves.
* EVM curves.
* PSD plots.
* Constellation diagrams.
* Time-domain waveforms.
* Algorithm-comparison tables.
* Benchmark reports.

Large generated outputs will remain excluded from normal source-control tracking unless explicitly selected for archival or publication purposes.

---

# Visualization

Planned visualization components include:

* PAPR CCDF curves.
* BER versus SNR.
* SER versus SNR.
* EVM versus SNR.
* PSD comparisons.
* Time-domain OFDM waveforms.
* Constellation diagrams.
* PAPR distribution histograms.
* Algorithm-comparison plots.
* Complexity-versus-performance plots.
* Runtime benchmarks.
* Parameter-sensitivity plots.

All scientific figures should be generated from reproducible experiment data rather than manually edited plots.

---

# Validation and Verification

The project will introduce multiple layers of verification.

### Unit Testing

Individual components will be tested independently, including:

* Modulators.
* Demodulators.
* FFT/IFFT processing.
* Cyclic-prefix processing.
* PAPR measurement.
* PAPR-reduction algorithms.
* Channel models.
* Equalizers.
* Metric calculations.

### Integration Testing

End-to-end tests will validate:

* Transmitter → channel → receiver operation.
* OFDM reconstruction.
* Baseline BER behavior.
* PAPR-reduction integration.
* Channel/equalizer compatibility.
* Configuration reproducibility.

### Scientific Validation

Simulation results will be compared against:

* Analytical expectations.
* Established communication-theory relationships.
* Reference implementations where appropriate.
* Published scientific results.
* Standardized or literature-based simulation configurations.

The objective is to distinguish software correctness from scientific validity.

---

# Software Quality

Planned software-quality improvements include:

* Automated unit testing.
* Integration testing.
* Static type checking.
* Code formatting.
* Linting.
* Continuous integration.
* Documentation generation.
* API documentation.
* Code coverage measurement.
* Reproducible development environments.
* Dependency management.

---

# Documentation

Planned documentation will include:

* Installation guide.
* Quick-start guide.
* Architecture documentation.
* API documentation.
* OFDM theory background.
* PAPR theory background.
* PAPR-reduction methodology.
* Channel-model documentation.
* Configuration reference.
* Experiment guide.
* Benchmarking guide.
* Reproducibility guide.
* Scientific methodology documentation.
* Example experiments.

---

# Benchmarking

A dedicated benchmarking framework is planned for comparing PAPR-reduction techniques under controlled conditions.

Benchmark dimensions will include:

* PAPR reduction.
* BER impact.
* EVM impact.
* PSD impact.
* Computational complexity.
* Execution time.
* Memory requirements.
* Parameter sensitivity.
* Robustness across channel conditions.

The goal is to evaluate algorithms using a multi-dimensional performance perspective rather than PAPR reduction alone.

---

# Scientific Reporting

Future releases may include automated generation of:

* Experiment summaries.
* Parameter tables.
* Performance tables.
* PAPR comparison tables.
* BER comparison tables.
* Algorithm rankings.
* Statistical summaries.
* Publication-ready figures.
* Reproducibility metadata.

---

# [0.1.0] - 2026-08-28

## Added

### Initial Repository

* Initial public release of **OFDM-PAPR-LinkSim**.
* Initial Git repository and project structure.
* Initial Python package architecture.
* Initial scientific project documentation.
* Initial project README.
* Initial MIT License.
* Initial citation metadata.
* Initial changelog.

### Project Architecture

Established the initial modular architecture for an end-to-end OFDM communication-link simulator.

The planned architecture separates the communication system into logically independent components:

* Source processing.
* Bit generation.
* CRC.
* Channel coding.
* Interleaving.
* Digital modulation.
* OFDM modulation.
* PAPR analysis.
* PAPR reduction.
* Channel modeling.
* Synchronization impairments.
* Channel estimation.
* Equalization.
* OFDM demodulation.
* Symbol demapping.
* Channel decoding.
* Performance evaluation.
* Experiment management.
* Result analysis.

### Repository Structure

Established top-level directories for:

* `src/`
* `tests/`
* `examples/`
* `configs/`
* `docs/`
* `results/`
* `references/`
* `analyzers/`
* `experiments/`
* `papr_methods/`
* `scenarios/`

The directory structure is intended to maintain separation between:

* Core implementation.
* Experimental code.
* Configuration.
* Testing.
* Documentation.
* Generated results.
* Scientific analysis.

### Python Packaging

Added `pyproject.toml` containing:

* Project metadata.
* Package name and version.
* Python version requirements.
* Runtime dependencies.
* Development dependencies.
* Documentation dependencies.
* Package discovery configuration.
* Package-data configuration.
* Pytest configuration.
* Ruff configuration.
* Black configuration.
* Mypy configuration.

### Runtime Dependencies

Initial runtime dependencies include:

* NumPy.
* SciPy.
* Matplotlib.
* Pandas.
* tqdm.
* PyYAML.

These dependencies provide the initial numerical-computing, scientific-analysis, visualization, data-processing, progress-reporting, and configuration infrastructure.

### Development Tooling

Initial development tooling includes:

* pytest.
* pytest-cov.
* Ruff.
* Black.
* Mypy.

These tools establish the foundation for automated testing, code quality, formatting, and static type analysis.

### Documentation Infrastructure

Initial documentation support includes:

* README-based project documentation.
* Sphinx documentation infrastructure.
* Scientific documentation structure.
* Project citation metadata.

### Python Support

Initial support for:

* Python 3.10
* Python 3.11
* Python 3.12

The minimum supported Python version is **Python 3.10**.

---

# Project Scope

The `0.1.0` release establishes the initial research and software-engineering baseline for a modular OFDM simulation framework.

The primary research scope is the systematic study of PAPR in OFDM systems and the evaluation of PAPR-reduction techniques under controlled communication-system conditions.

The framework is intended to eventually support investigations involving:

* OFDM waveform generation.
* PAPR characterization.
* PAPR-reduction techniques.
* AWGN and fading channels.
* Synchronization impairments.
* Receiver equalization.
* BER analysis.
* EVM analysis.
* PSD analysis.
* Computational-complexity analysis.
* Reproducible simulation.
* Algorithmic benchmarking.

---

# Scientific Methodology

The project is designed around a controlled simulation methodology.

A typical experiment is expected to follow the processing chain:

```text
Random Bit Source
        │
        ▼
Channel Coding
        │
        ▼
Interleaving
        │
        ▼
Digital Modulation
        │
        ▼
OFDM Mapping
        │
        ▼
IFFT
        │
        ▼
PAPR Measurement
        │
        ▼
PAPR Reduction
        │
        ▼
Channel
        │
        ▼
Synchronization / Impairments
        │
        ▼
Channel Estimation
        │
        ▼
Equalization
        │
        ▼
FFT
        │
        ▼
Demodulation
        │
        ▼
De-interleaving
        │
        ▼
Channel Decoding
        │
        ▼
CRC / Bit Recovery
        │
        ▼
Performance Evaluation
```

This architecture is intended to allow individual processing stages to be replaced, configured, tested, and benchmarked independently.

---

# Current Development Status

**Version 0.1.0 — Initial Research Architecture**

The project is currently in the foundational development stage.

At this stage:

* Repository architecture has been established.
* Python packaging configuration has been established.
* Scientific documentation has been established.
* Citation and licensing metadata have been established.
* Testing and code-quality infrastructure has been defined.
* Core communication-system modules are being developed.
* Standardized simulation parameters are being established.
* PAPR-reduction algorithms are planned but not yet considered production-ready.
* Scientific validation is pending implementation of the baseline communication chain.

Therefore, numerical results should not be interpreted as validated benchmark results until the corresponding simulation modules and validation procedures have been implemented.

---

# Release Philosophy

Future releases will distinguish between:

* **Architectural releases** — major structural changes.
* **Feature releases** — new communication-system capabilities or algorithms.
* **Research releases** — validated experimental functionality.
* **Maintenance releases** — bug fixes and compatibility updates.

Experimental functionality may remain under `Unreleased` until it satisfies the project's testing and validation requirements.

---

# Versioning

The project follows **Semantic Versioning** (`MAJOR.MINOR.PATCH`):

* **MAJOR** — incompatible API, architecture, or behavior changes.
* **MINOR** — backward-compatible functionality additions.
* **PATCH** — backward-compatible bug fixes, corrections, and minor improvements.

Examples:

```text
0.1.0 → Initial research architecture
0.2.0 → Baseline OFDM communication chain
0.3.0 → PAPR analysis framework
0.4.0 → Initial PAPR-reduction algorithms
0.5.0 → Channel and synchronization models
1.0.0 → Validated stable research framework
```

These version examples represent a possible development trajectory and are not binding release commitments.

---

# Changelog Guidelines

Future entries should document meaningful changes using categories such as:

* **Added** — new functionality.
* **Changed** — changes to existing functionality.
* **Deprecated** — functionality scheduled for removal.
* **Removed** — removed functionality.
* **Fixed** — bug fixes.
* **Security** — security-related changes.
* **Scientific** — changes affecting simulation methodology or scientific validity.
* **Validation** — newly validated models, algorithms, or results.
* **Performance** — computational-performance improvements.

Changes affecting scientific results should explicitly document relevant parameter, algorithm, model, or methodology changes.

---

# Links

* [Repository](https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link)
* [Issues](https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link/issues)
* [README](https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link#readme)
* [Changelog](https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link/blob/main/CHANGELOG.md)

---

[Unreleased]: https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/M-Amin-Wolverine/ofdm-papr-communication-link/releases/tag/v0.1.0

