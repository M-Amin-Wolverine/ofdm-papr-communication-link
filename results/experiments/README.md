# OFDM-PAPR-LinkSim — Technical Analysis of PAPR Reduction Methods

> **Experimental snapshot:** `compare_papr_methods.py`  
> **Configuration:** 8 OFDM blocks, QPSK, SNR = 15 dB, FFT size = 256, deterministic seed = 42  
> **Purpose:** Technical interpretation of the current PAPR-reduction implementation and its measured behavior.

---

## 1. Executive Summary

This document analyzes the current experimental behavior of the PAPR-reduction methods implemented in **OFDM-PAPR-LinkSim**. The comparison is based on an actual `compare_papr_methods` run rather than on theoretical expectations alone.

The central observation is that the methods are **not equivalent optimizers**. They modify the OFDM waveform through fundamentally different mechanisms:

- **NONE** establishes the unmodified OFDM reference.
- **Clipping** directly limits large time-domain peaks and therefore produces the largest immediate PAPR reduction in this test, at the cost of nonlinear distortion.
- **SLM (Selected Mapping)** searches among phase-rotated but information-equivalent candidate waveforms and selects a low-PAPR candidate. Its effectiveness depends strongly on the number and quality of candidates and on side-information handling.
- **PTS (Partial Transmit Sequences)** independently phase-rotates subblocks and searches for a combination minimizing the composite peak. Its performance is highly sensitive to partitioning and candidate-search complexity.
- **Tone Reservation (TR)** reserves non-data subcarriers and uses them to synthesize a peak-canceling signal. It can preserve data-bearing carriers conceptually, but consumes spectral resources and depends strongly on the reserved-tone configuration and optimization algorithm.
- **ACE (Active Constellation Extension)** modifies selected constellation points within allowed regions to reduce time-domain peaks. It is a constrained optimization problem rather than simple clipping, and its EVM behavior depends on the extension strategy and implementation constraints.

The current results therefore should be interpreted as a **functional implementation benchmark**, not yet as a publication-grade algorithmic ranking. In particular, the current PTS and TR configurations appear intentionally lightweight, so their measured performance should not be generalized to the algorithms in their full research-grade forms.

---

## 2. Experimental Configuration

The reported experiment uses the same underlying transmission data for the compared methods so that differences are attributable primarily to the PAPR-processing stage.

| Parameter | Current Test Value |
|---|---:|
| Number of OFDM blocks | 8 |
| Modulation | QPSK |
| FFT size | 256 |
| SNR | 15 dB |
| Random seed | 42 |
| Channel | AWGN-style baseline comparison |
| PAPR metric | Linear PAPR converted to dB |
| RX side-information | Enabled for SLM / PTS |
| Compared methods | NONE, Clipping, SLM, PTS, Tone Reservation, ACE |

### Why identical input matters

A valid algorithm comparison requires the methods to see equivalent information symbols and equivalent channel conditions. Otherwise, differences in BER, EVM, or PAPR can be caused by different random payloads or channel realizations rather than by the PAPR algorithm itself.

The deterministic seed further improves reproducibility. It does **not**, however, mean that one eight-block run is statistically sufficient for a final scientific conclusion.

---

## 3. Measured Results

### 3.1 Primary comparison

| Method | PAPR [dB] | BER [%] | EVM [%] | ΔPAPR vs. NONE [dB] | Main Mechanism |
|---|---:|---:|---:|---:|---|
| **NONE** | **9.40** | **0.0** | **7.7** | 0.00 | Unmodified OFDM |
| **Clipping** | **4.03** | **0.0** | **13.0** | **−5.37** | Direct peak limiting |
| **SLM** | **8.72** | **0.0** | **7.7** | **−0.68** | Candidate phase rotation |
| **PTS** | **9.09** | **0.0** | **7.7** | **−0.31** | Subblock phase optimization |
| **Tone Reservation** | **8.45** | **3.5e−2** | **31.4** | **−0.95** | Reserved-tone peak cancellation |
| **ACE** | **5.68** | **0.0** | **23.5** | **−3.72** | Constrained constellation extension |

> **Important:** The earlier interpretation that SLM reduced PAPR by `1.40 dB` was based on an inconsistent comparison. With the measured baseline of 9.40 dB and SLM at 8.72 dB, the actual reduction is **0.68 dB**. Likewise, PTS provides **0.31 dB** reduction, not a large reduction. The table above uses the numerically consistent values.

---

## 4. Baseline: NONE

The `none` configuration is the scientific reference.

Measured:

- PAPR = **9.40 dB**
- BER = **0%**
- EVM = **7.7%**

No PAPR-reduction operation is applied. Consequently, the transmitter emits the natural OFDM superposition of independently modulated subcarriers.

### Why PAPR is high in OFDM

For an OFDM signal,

$$\[x[n] = \frac{1}{\sqrt{N}}\sum_{k=0}^{N-1} X_k e^{j2\pi kn/N}\]$$

many independently phased subcarriers can add constructively at particular time instants. This creates occasional high-amplitude peaks even when the average signal power is moderate.

The PAPR is

$$\[\mathrm{PAPR}=\frac{\max_n |x[n]|^2}{\mathbb{E}[|x[n]|^2]}\]$$

and in dB:

$$\[\mathrm{PAPR}_{dB}=10\log_{10}(\mathrm{PAPR})\]$$

The 9.40 dB measurement is therefore the reference against which the reduction techniques should be evaluated.

---

## 5. Clipping

### Measured behavior

| Metric | NONE | Clipping |
|---|---:|---:|
| PAPR | 9.40 dB | **4.03 dB** |
| BER | 0% | 0% |
| EVM | 7.7% | **13.0%** |
| PAPR reduction | — | **5.37 dB** |

Clipping is the most direct approach:

$$\[x_c[n] =\begin{cases}x[n], & |x[n]|\le A\\A e^{j\angle x[n]}, & |x[n]|>A\end{cases}\]$$

where $$\(A\)$$ is the clipping threshold.

### Interpretation

The measured reduction of **5.37 dB** is substantial. This is exactly what should be expected from a method that explicitly attacks the time-domain amplitude peaks.

The price is nonlinear distortion.

Clipping introduces:

1. **In-band distortion**
2. **Out-of-band spectral regrowth**
3. **Constellation displacement**
4. **Potential BER degradation**
5. **Higher EVM**

The current result shows this trade-off clearly:

> PAPR falls from **9.40 → 4.03 dB**, while EVM rises from **7.7 → 13.0%**.

Interestingly, BER remains zero at this particular SNR and short test length. This does **not** prove that clipping is BER-neutral. It only means the accumulated distortion was insufficient to cause a detected bit error in this experiment.

### Engineering conclusion

Clipping is currently the strongest low-complexity PAPR reducer in the benchmark, but it should never be evaluated using PAPR alone.

A meaningful clipping study must also measure:

- EVM
- BER vs. SNR
- PSD / spectral regrowth
- ACLR or adjacent-channel leakage
- clipping ratio
- clipping noise power

---

## 6. Selected Mapping (SLM)

SLM does not directly distort the OFDM waveform through amplitude clipping.

Instead, multiple statistically equivalent candidates are constructed:

$$\[X^{(u)}_k = X_k B^{(u)}_k\]$$

where $$\(B^{(u)}_k\)$$ is a phase sequence, commonly satisfying

$$\[|B^{(u)}_k|=1.$$\]$$

Each candidate produces a different time-domain waveform:

$$\[x^{(u)} = \mathrm{IFFT}\{X^{(u)}\}\]$$

and the candidate with minimum PAPR is selected.

### Measured behavior

SLM:

- PAPR = **8.72 dB**
- BER = **0%**
- EVM = **7.7%**
- PAPR reduction = **0.68 dB**

### Why the reduction is modest

This result is technically plausible for a lightweight SLM configuration.

SLM effectiveness depends strongly on:

- number of candidate phase sequences \(U\)
- statistical independence of candidates
- phase-sequence design
- subcarrier partitioning
- random-sequence generation
- candidate-selection metric

If only a small candidate population is searched, the probability of finding a substantially lower-PAPR waveform is limited.

The key point is:

> SLM does not guarantee a large reduction; it provides a probabilistic improvement whose quality increases with candidate diversity and search complexity.

### Side information

The receiver must know which phase sequence was selected.

Without that information, the receiver cannot reliably invert the transformation:

$$\[\hat X_k =\hat X^{(u)}_k / B^{(u)}_k.\]$$

Therefore, side-information recovery is essential for a fair end-to-end BER test.

The current test explicitly accounts for this for SLM.

### EVM behavior

SLM retains the measured EVM of **7.7%**, equal to the baseline.

That is a major conceptual advantage over clipping:

- SLM changes the waveform representation.
- It does not intentionally move constellation points through nonlinear amplitude limiting.

Its weakness is computational complexity and side-information overhead.

---

## 7. Partial Transmit Sequences (PTS)

PTS divides the frequency-domain data into multiple subblocks:

$$\[X =\sum_{v=1}^{V} X_v\]$$

and applies phase factors:

$$\[\tilde X =\sum_{v=1}^{V} b_v X_v\]$$

where

$$\[b_v = e^{j\phi_v}.\]$$

The receiver must know the selected phase combination.

### Measured behavior

PTS:

- PAPR = **9.09 dB**
- BER = **0%**
- EVM = **7.7%**
- PAPR reduction = **0.31 dB**

This is the smallest reduction among the active PAPR methods in the current test.

### This does NOT mean PTS is intrinsically ineffective

PTS can be very effective when sufficiently optimized.

The search space grows rapidly with the number of subblocks and allowed phase factors. For example, if there are \(V\) subblocks and \(W\) possible phase factors, exhaustive search can approach:

$$\[W^{V-1}\]$$

candidate combinations after fixing one reference phase.

Therefore, a lightweight implementation with:

- small $$\(V\)$$
- few candidate phase factors
- small candidate budget
- simplified partitioning

can easily produce only a small PAPR improvement.

### Current interpretation

The correct conclusion is:

> **The current PTS configuration is underpowered relative to the potential of the PTS algorithm.**

It is not scientifically correct to conclude that PTS is worse than SLM in general from this single configuration.

### Recommended PTS experiment

A proper sensitivity study should sweep:

- $$\(V \in \{2,4,8,16\}\)$$
- phase factors $$\(W \in \{2,4,8\}\)$$
- adjacent / interleaved / pseudo-random partitioning
- exhaustive vs. heuristic search

and report:

$$\[\text{PAPR reduction}\quad\text{vs.}\quad\text{number of candidates}\]$$

This turns PTS into a meaningful complexity-performance study.

---

## 8. Tone Reservation (TR)

Tone Reservation uses dedicated subcarriers that do not carry information.

Let the OFDM signal be decomposed as:

$$\[x[n] = x_D[n] + x_R[n]\]$$

where:

- $$\(x_D[n]\)$$ contains data-bearing tones
- $$\(x_R[n]\)$$ is generated using reserved tones

The objective is to find a cancellation signal that reduces the peaks of \(x_D[n]\).

### Measured behavior

- PAPR = **8.45 dB**
- BER = **3.5e−2%**
- EVM = **31.4%**
- PAPR reduction = **0.95 dB**

### Why this result is unusual

Conceptually, TR should not need to alter the information-bearing constellation because reserved carriers are used for the cancellation waveform.

Therefore, the very high EVM of **31.4%** and the nonzero BER deserve additional investigation.

Possible causes include:

1. reserved-tone configuration
2. excessive cancellation amplitude
3. projection/optimization behavior
4. normalization mismatch
5. demodulation treatment of reserved carriers
6. data-tone indexing mismatch
7. receiver reconstruction assumptions
8. insufficient optimization convergence
9. PAPR being evaluated on a differently normalized signal
10. interaction between the current implementation and the measurement pipeline

This is an important engineering finding because it indicates that TR should receive additional validation before being used as a reference implementation.

### Scientific status

The current TR result should therefore be classified as:

> **Implementation-level result requiring validation, not evidence that conventional TR inherently produces 31.4% EVM.**

---

## 9. Active Constellation Extension (ACE)

ACE reduces peaks by moving selected constellation points within permitted extension regions.

The basic idea is:

$$\[X_k \rightarrow X_k + \Delta X_k\]$$

subject to constellation-dependent constraints.

The optimization seeks a modified symbol vector whose IFFT has lower peak amplitude while maintaining allowable constellation geometry.

### Measured behavior

- PAPR = **5.68 dB**
- BER = **0%**
- EVM = **23.5%**
- PAPR reduction = **3.72 dB**

ACE is therefore substantially more effective than SLM and the current PTS/TR configurations.

### But the EVM cost is significant

The current result shows:

$$\[9.40 \rightarrow 5.68\text{ dB}\]$$

while

$$\[7.7\% \rightarrow 23.5\%.\]$$

This indicates that the implementation is achieving a strong reduction in peak amplitude by allowing relatively large constellation displacement.

That creates an important research question:

> How much constellation extension is actually necessary to obtain a given PAPR reduction?

The answer should be determined using an optimization sweep rather than a single fixed configuration.

---

# 10. Cross-Method Comparison

## 10.1 PAPR effectiveness

Ranking the current implementations by measured PAPR:

1. **Clipping — 4.03 dB**
2. **ACE — 5.68 dB**
3. **Tone Reservation — 8.45 dB**
4. **SLM — 8.72 dB**
5. **PTS — 9.09 dB**
6. **NONE — 9.40 dB**

This is a ranking of the **current configurations**, not of the theoretical algorithms.

---

## 10.2 PAPR reduction relative to baseline

| Method | Baseline PAPR | Method PAPR | Reduction |
|---|---:|---:|---:|
| Clipping | 9.40 dB | 4.03 dB | **5.37 dB** |
| ACE | 9.40 dB | 5.68 dB | **3.72 dB** |
| Tone Reservation | 9.40 dB | 8.45 dB | **0.95 dB** |
| SLM | 9.40 dB | 8.72 dB | **0.68 dB** |
| PTS | 9.40 dB | 9.09 dB | **0.31 dB** |

The ranking demonstrates a critical principle:

> PAPR reduction is strongly dependent on implementation budget and parameterization.

---

# 11. PAPR vs. EVM Trade-off

One of the most important results is that PAPR cannot be optimized independently of signal quality.

| Method | PAPR [dB] | EVM [%] | Interpretation |
|---|---:|---:|---|
| NONE | 9.40 | 7.7 | Reference |
| Clipping | **4.03** | 13.0 | Very strong reduction, moderate distortion |
| SLM | 8.72 | **7.7** | Small reduction, essentially baseline EVM |
| PTS | 9.09 | **7.7** | Very small reduction, baseline EVM |
| TR | 8.45 | **31.4** | Small reduction, unexpectedly high EVM |
| ACE | 5.68 | **23.5** | Strong reduction, high constellation displacement |

This produces two qualitatively different families:

### Waveform-selection / phase-based methods

- SLM
- PTS

These primarily change the representation of the signal and can preserve constellation quality, but require search complexity and potentially side information.

### Signal-distortion / signal-modification methods

- Clipping
- ACE
- TR

These modify the waveform or signal representation more aggressively and therefore require careful quality constraints.

---

# 12. BER Interpretation

The measured BER values are:

- NONE: 0%
- Clipping: 0%
- SLM: 0%
- PTS: 0%
- TR: 3.5e−2%
- ACE: 0%

At first glance, this might suggest that all methods except TR are BER-neutral.

That conclusion would be premature.

Only **8 OFDM blocks** were tested. With a finite number of transmitted bits, zero observed errors means:

$$\[\mathrm{BER}_{observed}=0\]$$

not

$$\[\mathrm{BER}_{true}=0.\]$$

A statistically meaningful BER experiment requires many more transmitted bits.

For example, if no errors are observed after \(N\) transmitted bits, the experiment can still only establish an upper bound on the underlying BER with a chosen confidence level.

Therefore, BER should be evaluated over:

- thousands or millions of bits
- multiple random seeds
- multiple SNR values
- multiple channel realizations

---

# 13. Why One Test Is Not Enough

The current experiment is extremely useful for debugging and functional verification, but it is not sufficient for algorithmic generalization.

A publication-grade evaluation should introduce Monte Carlo averaging.

For each configuration:

$$\[\bar M =\frac{1}{R}\sum_{r=1}^{R} M_r\]$$

where $$\(R\)$$ is the number of independent random trials.

For PAPR, reporting only the mean is also insufficient.

The preferred representation is the **CCDF**:

$$\[\mathrm{CCDF}(z)=P(\mathrm{PAPR}>z).\]$$

This allows two algorithms to be compared across the complete tail behavior rather than at one observed maximum.

---

# 14. PAPR CCDF Should Become the Primary Scientific Figure

For OFDM PAPR research, the most informative comparison is typically:

$$\[P(\mathrm{PAPR}>z)\]$$

versus $$\(z\)$$ in dB.

Recommended curves:

- NONE
- Clipping
- SLM
- PTS
- TR
- ACE

A useful reporting point is:

$$\[\mathrm{PAPR}_{0.1\%}\]$$

meaning the PAPR exceeded only 0.1% of the time.

Other useful points:

- 10%
- 1%
- 0.1%
- 0.01%

This is much more robust than comparing one PAPR number from eight blocks.

---

# 15. Complexity Must Be Measured

PAPR reduction is only one dimension of the problem.

A complete engineering comparison should measure:

| Dimension | Why it matters |
|---|---|
| PAPR | PA back-off requirement |
| BER | Communication reliability |
| EVM | Modulation quality |
| PSD | Spectral integrity |
| ACLR | Adjacent-channel interference |
| Throughput | Data efficiency |
| Complexity | Hardware/software cost |
| Latency | Real-time feasibility |
| Side information | Receiver overhead |
| Spectral efficiency | Resource utilization |
| Memory | Implementation footprint |

A method that achieves 3 dB more PAPR reduction but requires 100× the computational complexity may be less attractive in a practical transmitter.

---

# 16. Recommended Complexity Metrics

The simulator should eventually expose at least:

### SLM

- number of candidates \(U\)
- number of IFFTs
- phase-sequence generation cost
- side-information bits

### PTS

- number of subblocks \(V\)
- number of phase factors \(W\)
- number of candidate combinations
- exhaustive/heuristic search mode
- IFFT-equivalent complexity

### TR

- number of reserved tones
- number of optimization iterations
- projection iterations
- cancellation-vector norm

### ACE

- number of iterations
- number of active constellation points
- optimization tolerance
- maximum extension magnitude

### Clipping

- clipping ratio
- clipping threshold
- filtering iterations

---

# 17. Important Implementation Observation: Fairness

A fair comparison must distinguish between:

### Algorithmic capability

What the underlying mathematical method can achieve with adequate optimization.

### Current implementation configuration

What this repository currently achieves under the selected parameters.

The present results are primarily evidence about the second category.

For example:

> PTS = 9.09 dB

does **not** mean:

> PTS is inherently ineffective.

It means:

> Under the current PTS partition, phase-factor set, and candidate-search budget, the implementation produced only 0.31 dB of reduction.

This distinction is essential for scientifically defensible conclusions.

---

# 18. Recommended Next Experiment Matrix

A stronger experimental campaign should sweep:

## FFT size

$$\[N \in \{16,64,128,256,512,1024,2048,4096,8192\}\]$$

## Modulation

- QPSK
- 16-QAM
- 64-QAM
- 256-QAM
- 1024-QAM

## Oversampling

$$\[L \in \{1,2,4,8,16\}\]$$

## SNR

For example:

$$\[0,5,10,15,20,25,30\ \mathrm{dB}\]$$

## Channel

- AWGN
- Rayleigh
- Rician

## PAPR methods

- NONE
- Clipping
- Clipping + Filtering
- SLM
- PTS
- Tone Reservation
- ACE

This creates a real experimental design rather than a single point comparison.

---

# 19. Recommended Scientific Output Set

For every method, the simulator should eventually generate:

### Figure 1 — PAPR CCDF

$$\[P(\mathrm{PAPR}>z)\]$$

### Figure 2 — BER vs. SNR

$$\[BER(SNR)\]$$

### Figure 3 — EVM vs. SNR

$$\[EVM(SNR)\]$$

### Figure 4 — PSD

Power spectral density before and after PAPR reduction.

### Figure 5 — Constellation

Received constellation under identical channel conditions.

### Figure 6 — Time-domain waveform

Peak behavior before and after processing.

### Figure 7 — Complexity vs. PAPR

For example:

$$\[\text{computational cost}\quad\text{vs.}\quad\text{PAPR reduction}\]$$

This final figure can be particularly valuable for a research paper.

---

# 20. Suggested Composite Score

A future experiment can optionally define a multi-objective score rather than selecting the lowest PAPR blindly.

For example:

$$\[J =w_P \cdot \mathrm{PAPR}+w_E \cdot \mathrm{EVM}+w_B \cdot \mathrm{BER}+w_C \cdot C+w_S \cdot S\]$$

where:

- $$\(C\)$$ = computational complexity
- $$\(S\)$$ = side-information / spectral overhead
- $$\(w_i\)$$ = application-specific weights

However, this score should **not replace raw metrics**. Raw PAPR, BER, EVM, PSD and complexity must remain available so that researchers can change the weighting without rerunning the physical simulation.

---

# 21. Current Technical Verdict

The current repository has moved beyond a trivial "PAPR demo" because the comparison already exposes the fundamental trade-offs among multiple PAPR-reduction families.

The measured benchmark can be summarized as follows:

### Best immediate PAPR reduction

**Clipping**

$$\[9.40 \rightarrow 4.03\ \mathrm{dB}\]$$

with a measurable EVM penalty.

### Best non-clipping reduction in the current test

**ACE**

$$\[9.40 \rightarrow 5.68\ \mathrm{dB}\]$$

but with a comparatively large EVM increase.

### Most constellation-preserving methods

**SLM and PTS**

Both retain the baseline EVM of approximately **7.7%**, but the current search configurations provide only modest PAPR reduction.

### Most suspicious current result

**Tone Reservation**

The combination of only **0.95 dB** PAPR reduction with **31.4% EVM** and nonzero BER warrants implementation-level debugging and validation before scientific conclusions are drawn.

### Most important methodological warning

The current PTS and SLM results should not be interpreted as theoretical limits. Their performance is strongly dependent on candidate count, partitioning, phase-set design, and search budget.

---

# 22. Recommended Development Priorities

## Priority 1 — Validate the measurement pipeline

Verify:

- normalization
- PAPR sample domain
- oversampling
- useful-sample extraction
- FFT/IFFT scaling
- CP treatment
- EVM reference definition
- BER bit alignment

## Priority 2 — Validate TR

Investigate why TR produces:

$$\[EVM=31.4\%\]$$

and nonzero BER despite using reserved carriers.

## Priority 3 — Expand SLM

Add configurable:

- $$\(U\)$$ candidate count
- phase alphabets
- deterministic/random phase sequences
- side-information representation

## Priority 4 — Expand PTS

Add configurable:

- $$\(V\)$$
- $$\(W\)$$
- partition strategy
- exhaustive search
- iterative/heuristic search

## Priority 5 — Add clipping + filtering

This is essential because raw clipping alone creates spectral regrowth.

## Priority 6 — Add Monte Carlo

Use hundreds or thousands of blocks/trials rather than eight blocks for final comparisons.

## Priority 7 — Add CCDF

Make CCDF a first-class analyzer and report PAPR percentile values.

---

# 23. Bottom Line

The current experiment demonstrates that the PAPR problem is fundamentally a **multi-objective optimization problem**.

There is no universally best method.

The observed trade-off is approximately:

$$\[\boxed{\text{Lower PAPR}\quad\Longleftrightarrow\quad\text{Distortion / Complexity / Overhead}}\]$$

The current benchmark illustrates this directly:

- **Clipping** obtains the lowest PAPR with nonlinear distortion.
- **ACE** obtains a strong reduction by modifying constellation geometry.
- **SLM** obtains a smaller reduction while preserving EVM, at the cost of candidate search and side information.
- **PTS** preserves EVM but currently has insufficient search/partition complexity to produce a large reduction.
- **TR** theoretically offers a powerful distortion-avoidance mechanism through reserved carriers, but the current implementation exhibits anomalous EVM/BER behavior that must be investigated.
- **NONE** remains indispensable as the reference baseline.

The next scientific step is therefore **not simply to add more PAPR algorithms**. It is to make the existing comparison experimentally rigorous: Monte Carlo trials, PAPR CCDF, SNR sweeps, channel sweeps, oversampling, modulation sweeps, complexity accounting, PSD/ACLR analysis, and systematic parameter sensitivity.
