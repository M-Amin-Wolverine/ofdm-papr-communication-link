"""
Configuration management for OFDM-PAPR-LinkSim
==============================================

Centralized, typed, reproducible configuration management for the
OFDM-PAPR-LinkSim simulation framework.

Configuration flow
------------------

    baseline.yaml
          │
          ▼
    YAML parser
          │
          ▼
    ExperimentConfig
          │
     ┌────┴────┐
     │         │
 validation   snapshot
     │         │
     ▼         ▼
  Pipeline   Results

Design principles
-----------------
1. YAML is the human-editable configuration surface.
2. Dataclasses provide the typed Python configuration contract.
3. Configuration loading is deterministic and side-effect free.
4. Every load produces a new ``ExperimentConfig`` instance.
5. Reference/baseline constraints are explicit and auditable.
6. Invalid physical or simulation parameters fail early.
7. Configuration fingerprints provide experiment identity.
8. Random-stream identifiers remain centralized and reproducible.
9. Raw YAML is preserved for traceability.
10. Configuration serialization is deterministic.

The module supports both:

- YAML files
- Python mappings / dictionaries

The primary Stage-1 configuration is:

    configs/baseline.yaml

Stage-1 reference philosophy
----------------------------
The locked baseline represents the reference OFDM link against which
future PAPR-reduction experiments can be compared.

Typical baseline properties are:

- uncoded transmission
- no interleaving
- AWGN channel
- no fading
- no synchronization impairment
- no PAPR reduction
- deterministic random seed
- centralized RNG streams
- fixed OFDM configuration
- reproducible output

Future experiments can override these settings explicitly while the
baseline itself remains reproducible and auditable.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import warnings
from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

import numpy as np

try:
    import yaml
except ImportError as _yaml_exc:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


from ofdm_linksim.core.types import (
    CCDF_REPORT_PROBABILITIES,
    DEFAULT_CP_LENGTH,
    DEFAULT_FFT_SIZE,
    DEFAULT_OFDM_BLOCKS,
    DEFAULT_OVERSAMPLING,
    DEFAULT_SEED,
    ChannelType,
    CodingType,
    ConfigSnapshot,
    EqualizerType,
    FFTNormalization,
    InterleavingType,
    MappingType,
    ModulationType,
    PAPRMethod,
    SNRDefinition,
    validate_fft_size,
    validate_oversampling,
    validate_positive_integer,
    validate_snr_db,
)

from ofdm_linksim.utils.random import DEFAULT_STREAMS


# =============================================================================
# Public type aliases
# =============================================================================

PathLike = Union[str, os.PathLike]


# =============================================================================
# Generic validation helpers
# =============================================================================


def _require_non_negative_float(
    value: float,
    name: str,
) -> float:
    """Validate and normalize a finite non-negative float."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number.")

    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"{name} must be a real number."
        ) from exc

    if not np.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    if value < 0.0:
        raise ValueError(f"{name} cannot be negative.")

    return value


def _require_positive_float(
    value: float,
    name: str,
) -> float:
    """Validate and normalize a finite positive float."""
    value = _require_non_negative_float(value, name)

    if value <= 0.0:
        raise ValueError(f"{name} must be greater than zero.")

    return value


def _require_non_negative_int(
    value: int,
    name: str,
) -> int:
    """Validate and normalize a non-negative integer."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer.")

    if not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer.")

    value = int(value)

    if value < 0:
        raise ValueError(f"{name} cannot be negative.")

    return value


def _normalize_enum_key(value: Any) -> str:
    """Normalize a configuration enum/string key."""
    return (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


# =============================================================================
# Path helpers
# =============================================================================


def _repo_root_candidates() -> List[Path]:
    """
    Return plausible repository roots relative to this module.

    The source-tree layout is expected to resemble:

        repository/
        ├── configs/
        ├── src/
        │   └── ofdm_linksim/
        │       └── config.py
        └── ...

    The current working directory is also considered for development
    and installed-package scenarios.
    """
    here = Path(__file__).resolve()

    candidates: List[Path] = []

    if len(here.parents) > 2:
        candidates.append(here.parents[2])

    if len(here.parents) > 3:
        candidates.append(here.parents[3])

    candidates.extend(
        [
            Path.cwd(),
            Path.cwd().parent,
        ]
    )

    # Remove duplicates while preserving order.
    unique: List[Path] = []

    for candidate in candidates:
        candidate = candidate.resolve()

        if candidate not in unique:
            unique.append(candidate)

    return unique


def default_baseline_path() -> Path:
    """
    Locate the default ``configs/baseline.yaml``.

    Returns
    -------
    Path
        Existing baseline path if found; otherwise the conventional
        relative path ``configs/baseline.yaml``.
    """
    for root in _repo_root_candidates():
        candidate = root / "configs" / "baseline.yaml"

        if candidate.is_file():
            return candidate

    return Path("configs") / "baseline.yaml"


def default_configs_dir() -> Path:
    """Return the directory containing the default baseline."""
    baseline = default_baseline_path()

    if baseline.parent.name == "configs":
        return baseline.parent

    return Path("configs")


# =============================================================================
# Nested configuration sections
# =============================================================================


@dataclass(slots=True)
class ScenarioSection:
    """Experiment/scenario identity and lifecycle metadata."""

    name: str = "reference_baseline"
    version: str = "1.1"
    description: str = ""
    status: str = "locked"
    reference: bool = True
    purpose: Tuple[str, ...] = ()
    papr_reduction: str = "none"

    def is_locked(self) -> bool:
        """Return True when the scenario is explicitly reference-locked."""
        return (
            str(self.status).strip().lower() == "locked"
            or bool(self.reference)
        )


@dataclass(slots=True)
class RandomSection:
    """Global reproducibility and random-stream configuration."""

    seed: int = DEFAULT_SEED
    deterministic: bool = True
    centralized: bool = True

    streams: Dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_STREAMS)
    )

    def __post_init__(self) -> None:
        self.seed = _require_non_negative_int(
            self.seed,
            "random.seed",
        )

        if not self.streams:
            self.streams = dict(DEFAULT_STREAMS)

        normalized: Dict[str, int] = {}

        for name, stream_id in self.streams.items():
            normalized[str(name)] = _require_non_negative_int(
                stream_id,
                f"random.streams[{name!r}]",
            )

        # Ensure the canonical simulator streams always exist.
        for name, stream_id in DEFAULT_STREAMS.items():
            normalized.setdefault(
                name,
                int(stream_id),
            )

        self.streams = normalized


@dataclass(slots=True)
class SimulationSection:
    """Global simulation workload configuration."""

    mode: str = "research"
    ofdm_blocks: int = DEFAULT_OFDM_BLOCKS
    development_ofdm_blocks: int = 10_000
    monte_carlo_iterations: int = 1
    early_stopping: bool = False

    def __post_init__(self) -> None:
        self.ofdm_blocks = int(self.ofdm_blocks)
        self.development_ofdm_blocks = int(
            self.development_ofdm_blocks
        )
        self.monte_carlo_iterations = int(
            self.monte_carlo_iterations
        )

        validate_positive_integer(
            self.ofdm_blocks,
            "ofdm_blocks",
        )

        validate_positive_integer(
            self.development_ofdm_blocks,
            "development_ofdm_blocks",
        )

        validate_positive_integer(
            self.monte_carlo_iterations,
            "monte_carlo_iterations",
        )

    def effective_ofdm_blocks(self) -> int:
        """Return the actual OFDM block count for the selected mode."""
        mode = _normalize_enum_key(self.mode)

        if mode in {"development", "dev", "debug"}:
            return self.development_ofdm_blocks

        return self.ofdm_blocks


@dataclass(slots=True)
class OFDMSection:
    """OFDM waveform and resource-grid configuration."""

    fft_size: int = DEFAULT_FFT_SIZE

    active_subcarriers: int = 200
    pilot_subcarriers: int = 8
    data_subcarriers: int = 192

    cyclic_prefix_length: int = DEFAULT_CP_LENGTH

    oversampling_factor: int = DEFAULT_OVERSAMPLING
    oversampling_method: str = "frequency_domain_zero_padding"

    fft_normalization: str = "unitary"

    dc_subcarrier: Optional[int] = None
    guard_subcarriers: bool = True

    mapping_type: str = "symmetric"
    include_dc: bool = False

    papr_include_cp: bool = False

    def __post_init__(self) -> None:
        self.fft_size = int(self.fft_size)
        self.active_subcarriers = int(self.active_subcarriers)
        self.pilot_subcarriers = int(self.pilot_subcarriers)
        self.data_subcarriers = int(self.data_subcarriers)
        self.cyclic_prefix_length = int(self.cyclic_prefix_length)
        self.oversampling_factor = int(self.oversampling_factor)

        validate_fft_size(self.fft_size)
        validate_oversampling(self.oversampling_factor)

        validate_positive_integer(
            self.active_subcarriers,
            "active_subcarriers",
        )

        validate_positive_integer(
            self.data_subcarriers,
            "data_subcarriers",
        )

        if self.pilot_subcarriers < 0:
            raise ValueError(
                "pilot_subcarriers cannot be negative."
            )

        if self.active_subcarriers > self.fft_size:
            raise ValueError(
                "active_subcarriers cannot exceed fft_size."
            )

        expected = (
            self.pilot_subcarriers
            + self.data_subcarriers
        )

        if self.active_subcarriers != expected:
            raise ValueError(
                "OFDM resource-grid mismatch: "
                f"active_subcarriers={self.active_subcarriers}, "
                f"pilot_subcarriers={self.pilot_subcarriers}, "
                f"data_subcarriers={self.data_subcarriers}. "
                f"Expected active_subcarriers={expected}."
            )

        if self.cyclic_prefix_length < 0:
            raise ValueError(
                "cyclic_prefix_length cannot be negative."
            )

        if self.cyclic_prefix_length > self.fft_size:
            raise ValueError(
                "cyclic_prefix_length cannot exceed fft_size."
            )

        if self.dc_subcarrier is not None:
            self.dc_subcarrier = int(self.dc_subcarrier)

    @property
    def fft_norm_enum(self) -> FFTNormalization:
        """Return the typed FFT normalization enum."""
        key = _normalize_enum_key(
            self.fft_normalization
        )

        table = {
            "unitary": FFTNormalization.UNITARY,
            "ortho": FFTNormalization.UNITARY,
            "backward": FFTNormalization.BACKWARD,
            "forward": FFTNormalization.FORWARD,
        }

        if key not in table:
            raise ValueError(
                "Unknown fft_normalization: "
                f"{self.fft_normalization!r}"
            )

        return table[key]

    @property
    def mapping_enum(self) -> MappingType:
        """Return the typed subcarrier mapping enum."""
        key = _normalize_enum_key(
            self.mapping_type
        )

        table = {
            "symmetric": MappingType.SYMMETRIC,
            "contiguous": MappingType.CONTIGUOUS,
            "custom": MappingType.CUSTOM,
        }

        if key not in table:
            raise ValueError(
                f"Unknown mapping type: {self.mapping_type!r}"
            )

        return table[key]


@dataclass(slots=True)
class ModulationSection:
    """Digital modulation configuration."""

    scheme: str = "QPSK"
    order: int = 4
    bits_per_symbol: int = 2
    mapping: str = "gray"

    normalize_average_power: bool = True
    target_average_symbol_energy: float = 1.0

    def __post_init__(self) -> None:
        self.bits_per_symbol = int(self.bits_per_symbol)
        self.order = int(self.order)

        if self.bits_per_symbol <= 0:
            raise ValueError(
                "bits_per_symbol must be positive."
            )

        expected_order = 1 << self.bits_per_symbol

        if self.order != expected_order:
            raise ValueError(
                "Modulation configuration mismatch: "
                f"order={self.order}, "
                f"bits_per_symbol={self.bits_per_symbol}. "
                f"Expected order={expected_order}."
            )

        self.target_average_symbol_energy = (
            _require_positive_float(
                self.target_average_symbol_energy,
                "target_average_symbol_energy",
            )
        )

    @property
    def modulation_enum(self) -> ModulationType:
        """Return the typed modulation enum."""
        key = (
            str(self.scheme)
            .strip()
            .upper()
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )

        table = {
            "QPSK": ModulationType.QPSK,
            "4QAM": ModulationType.QPSK,
            "16QAM": ModulationType.QAM16,
            "QAM16": ModulationType.QAM16,
            "64QAM": ModulationType.QAM64,
            "QAM64": ModulationType.QAM64,
            "256QAM": ModulationType.QAM256,
            "QAM256": ModulationType.QAM256,
            "1024QAM": ModulationType.QAM1024,
            "QAM1024": ModulationType.QAM1024,
        }

        if key not in table:
            raise ValueError(
                f"Unsupported modulation scheme: {self.scheme!r}"
            )

        return table[key]


@dataclass(slots=True)
class SourceSection:
    """Information-bit source configuration."""

    type: str = "random_bits"
    length: Union[str, int] = "derived"
    binary_alphabet: Tuple[int, ...] = (0, 1)

    def __post_init__(self) -> None:
        alphabet = tuple(
            int(x)
            for x in self.binary_alphabet
        )

        if alphabet != (0, 1):
            raise ValueError(
                "binary_alphabet must be exactly (0, 1)."
            )

        self.binary_alphabet = alphabet

        if isinstance(self.length, str):
            if self.length.strip().lower() != "derived":
                raise ValueError(
                    "source.length must be 'derived' or a positive integer."
                )

        else:
            self.length = _require_positive_int(
                self.length,
                "source.length",
            )

    def resolve_n_bits(
        self,
        *,
        data_subcarriers: int,
        bits_per_symbol: int,
        ofdm_blocks: int,
    ) -> int:
        """
        Resolve the final number of information bits.

        ``length='derived'`` uses:

            Nbits =
                data_subcarriers
                × bits_per_symbol
                × OFDM_blocks
        """
        if isinstance(self.length, str):
            return int(
                data_subcarriers
                * bits_per_symbol
                * ofdm_blocks
            )

        return int(self.length)


@dataclass(slots=True)
class CodingSection:
    """Forward-error-correction and CRC configuration."""

    enabled: bool = False
    scheme: str = "none"
    code_rate: float = 1.0

    crc_enabled: bool = False
    crc_width: int = 16

    def __post_init__(self) -> None:
        self.code_rate = _require_positive_float(
            self.code_rate,
            "coding.code_rate",
        )

        if self.code_rate > 1.0:
            raise ValueError(
                "coding.code_rate cannot exceed 1.0."
            )

        self.crc_width = int(self.crc_width)

        if self.crc_enabled and self.crc_width <= 0:
            raise ValueError(
                "coding.crc_width must be positive when CRC is enabled."
            )

    @property
    def coding_enum(self) -> CodingType:
        """Return the typed coding enum."""
        key = _normalize_enum_key(
            self.scheme
        )

        if (
            not self.enabled
            or key in {"none", "off", ""}
        ):
            return CodingType.NONE

        raise NotImplementedError(
            f"Coding scheme {self.scheme!r} is not implemented."
        )


@dataclass(slots=True)
class InterleavingSection:
    """Bit interleaving configuration."""

    enabled: bool = False
    type: str = "none"

    rows: Optional[int] = None
    cols: Optional[int] = None

    def __post_init__(self) -> None:
        if self.rows is not None:
            self.rows = _require_positive_int(
                self.rows,
                "interleaving.rows",
            )

        if self.cols is not None:
            self.cols = _require_positive_int(
                self.cols,
                "interleaving.cols",
            )

    @property
    def interleaving_enum(self) -> InterleavingType:
        """Return the typed interleaving enum."""
        key = _normalize_enum_key(
            self.type
        )

        if (
            not self.enabled
            or key in {"none", "off", ""}
        ):
            return InterleavingType.NONE

        raise NotImplementedError(
            f"Interleaving type {self.type!r} is not implemented."
        )


@dataclass(slots=True)
class ChannelSection:
    """Physical channel model configuration."""

    model: str = "AWGN"
    enabled: bool = True

    fading: bool = False

    snr_definition: str = "EsN0"

    rayleigh_enabled: bool = False
    rician_enabled: bool = False

    rician_k_factor_db: float = 3.0

    per_symbol_fading: bool = True

    def __post_init__(self) -> None:
        self.rician_k_factor_db = float(
            self.rician_k_factor_db
        )

        if not np.isfinite(
            self.rician_k_factor_db
        ):
            raise ValueError(
                "rician_k_factor_db must be finite."
            )

    @property
    def channel_enum(self) -> ChannelType:
        """Return the typed channel model enum."""
        key = str(self.model).strip().upper()

        table = {
            "AWGN": ChannelType.AWGN,
            "RAYLEIGH": ChannelType.RAYLEIGH,
            "RICIAN": ChannelType.RICIAN,
            "RICE": ChannelType.RICIAN,
        }

        if key not in table:
            raise ValueError(
                f"Unknown channel model: {self.model!r}"
            )

        return table[key]

    @property
    def snr_definition_enum(self) -> SNRDefinition:
        """Return the typed SNR-definition enum."""
        key = (
            str(self.snr_definition)
            .strip()
            .upper()
            .replace("/", "")
            .replace("-", "")
            .replace("_", "")
        )

        table = {
            "ESN0": SNRDefinition.EsN0,
            "EBN0": SNRDefinition.EbN0,
            "SNR": SNRDefinition.SNR,
        }

        if key not in table:
            raise ValueError(
                f"Unknown SNR definition: {self.snr_definition!r}"
            )

        return table[key]


@dataclass(slots=True)
class SNRSection:
    """SNR sweep configuration."""

    start_db: float = 0.0
    stop_db: float = 30.0
    step_db: float = 2.0

    values: Tuple[float, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        self.start_db = float(self.start_db)
        self.stop_db = float(self.stop_db)
        self.step_db = float(self.step_db)

        if self.step_db <= 0.0:
            raise ValueError(
                "snr.step_db must be positive."
            )

        if self.stop_db < self.start_db:
            raise ValueError(
                "snr.stop_db must be >= start_db."
            )

        self.values = tuple(
            float(v)
            for v in self.values
        )

        for value in self.values:
            validate_snr_db(value)

    def grid(self) -> np.ndarray:
        """
        Return the final SNR sweep.

        Explicit ``values`` take precedence over generated grids.
        """
        if self.values:
            return np.asarray(
                self.values,
                dtype=np.float64,
            )

        return np.arange(
            self.start_db,
            self.stop_db + 0.5 * self.step_db,
            self.step_db,
            dtype=np.float64,
        )


@dataclass(slots=True)
class SynchronizationSection:
    """Synchronization impairment configuration."""

    enabled: bool = False

    cfo_enabled: bool = False
    cfo_normalized: float = 0.0

    timing_enabled: bool = False
    timing_offset_samples: int = 0

    phase_enabled: bool = False
    phase_radians: float = 0.0

    def __post_init__(self) -> None:
        self.cfo_normalized = float(
            self.cfo_normalized
        )

        if not np.isfinite(self.cfo_normalized):
            raise ValueError(
                "cfo_normalized must be finite."
            )

        self.timing_offset_samples = int(
            self.timing_offset_samples
        )

        self.phase_radians = float(
            self.phase_radians
        )

        if not np.isfinite(self.phase_radians):
            raise ValueError(
                "phase_radians must be finite."
            )


@dataclass(slots=True)
class EqualizationSection:
    """Frequency-domain equalization configuration."""

    enabled: bool = False
    method: str = "none"

    def __post_init__(self) -> None:
        if not str(self.method).strip():
            self.method = "none"

    @property
    def equalizer_enum(self) -> EqualizerType:
        """Return the typed equalizer enum."""
        key = _normalize_enum_key(
            self.method
        )

        if (
            not self.enabled
            or key in {"none", "off", ""}
        ):
            return EqualizerType.NONE

        table = {
            "zf": EqualizerType.ZF,
            "mmse": EqualizerType.MMSE,
        }

        if key not in table:
            raise ValueError(
                f"Unknown equalizer method: {self.method!r}"
            )

        return table[key]


@dataclass(slots=True)
class PAPRSection:
    """PAPR processing and CCDF-analysis configuration."""

    method: str = "none"
    include_cp: bool = False

    ccdf_probabilities: Tuple[float, ...] = field(
        default_factory=lambda: tuple(
            CCDF_REPORT_PROBABILITIES
        )
    )

    analysis_enabled: bool = True

    def __post_init__(self) -> None:
        probabilities = tuple(
            float(p)
            for p in self.ccdf_probabilities
        )

        for probability in probabilities:
            if not (
                0.0 < probability < 1.0
            ):
                raise ValueError(
                    "PAPR CCDF probabilities must satisfy "
                    "0 < p < 1."
                )

        self.ccdf_probabilities = probabilities

    @property
    def papr_method_enum(self) -> PAPRMethod:
        """Return the typed PAPR-method enum."""
        key = _normalize_enum_key(
            self.method
        )

        table = {
            "none": PAPRMethod.NONE,
            "clipping": PAPRMethod.CLIPPING,
            "slm": PAPRMethod.SLM,
            "pts": PAPRMethod.PTS,
            "tone_reservation": PAPRMethod.TONE_RESERVATION,
            "tr": PAPRMethod.TONE_RESERVATION,
            "ace": PAPRMethod.ACE,
        }

        if key not in table:
            raise ValueError(
                f"Unknown PAPR method: {self.method!r}"
            )

        return table[key]


@dataclass(slots=True)
class MetricsSection:
    """Numerical metric configuration."""

    ber_enabled: bool = True
    evm_enabled: bool = True
    psd_enabled: bool = True
    constellation_enabled: bool = True
    waveform_enabled: bool = True

    psd_method: str = "welch"
    psd_window: str = "hann"

    psd_nperseg: int = 1024
    psd_noverlap: int = 512

    diagnostic_samples: int = 4096

    def __post_init__(self) -> None:
        self.psd_nperseg = _require_positive_int(
            self.psd_nperseg,
            "metrics.psd_nperseg",
        )

        self.psd_noverlap = _require_non_negative_int(
            self.psd_noverlap,
            "metrics.psd_noverlap",
        )

        if self.psd_noverlap >= self.psd_nperseg:
            raise ValueError(
                "metrics.psd_noverlap must be smaller than "
                "metrics.psd_nperseg."
            )

        self.diagnostic_samples = _require_positive_int(
            self.diagnostic_samples,
            "metrics.diagnostic_samples",
        )


@dataclass(slots=True)
class ResultsSection:
    """Persistent result-output configuration."""

    root_directory: str = "results/baseline"

    overwrite: bool = False

    save_raw_data: bool = True
    save_processed_data: bool = True
    save_configuration: bool = True
    save_metadata: bool = True
    save_summary: bool = True

    csv: bool = True
    json: bool = True
    numpy: bool = True

    dir_papr: str = "results/baseline/papr"
    dir_ber: str = "results/baseline/ber"
    dir_evm: str = "results/baseline/evm"
    dir_psd: str = "results/baseline/psd"
    dir_figures: str = "results/baseline/figures"
    dir_metadata: str = "results/baseline/metadata"


@dataclass(slots=True)
class VisualizationSection:
    """Scientific visualization configuration."""

    enabled: bool = True
    style: str = "scientific"

    papr_ccdf: bool = True
    ber_vs_snr: bool = True
    evm_vs_snr: bool = True
    constellation: bool = True
    psd: bool = True
    waveform: bool = True

    save_format: str = "png"
    dpi: int = 300

    transparent: bool = False
    show_interactive: bool = False

    def __post_init__(self) -> None:
        self.dpi = _require_positive_int(
            self.dpi,
            "visualization.dpi",
        )

        if not str(self.save_format).strip():
            raise ValueError(
                "visualization.save_format cannot be empty."
            )


@dataclass(slots=True)
class ValidationSection:
    """Reference-baseline validation policy."""

    enabled: bool = True
    strict: bool = True

    require_uncoded: bool = True
    require_no_interleaving: bool = True

    require_awgn: bool = True
    require_no_fading: bool = True

    require_no_synchronization_impairments: bool = True

    require_no_papr_reduction: bool = True

    require_fixed_seed: bool = True

    require_oversampling: bool = True
    require_cp_excluded_from_papr: bool = True

    require_reproducible_results: bool = True


# =============================================================================
# Aggregate configuration
# =============================================================================


@dataclass(slots=True)
class ExperimentConfig:
    """
    Fully resolved experiment configuration.

    ``ExperimentConfig`` is the machine-readable configuration contract
    consumed by the simulator, analyzers, and result writers.

    For normal operation prefer:

        load_config()
        load_baseline()

    instead of manually constructing this object.
    """

    scenario: ScenarioSection = field(
        default_factory=ScenarioSection
    )

    random: RandomSection = field(
        default_factory=RandomSection
    )

    simulation: SimulationSection = field(
        default_factory=SimulationSection
    )

    ofdm: OFDMSection = field(
        default_factory=OFDMSection
    )

    modulation: ModulationSection = field(
        default_factory=ModulationSection
    )

    source: SourceSection = field(
        default_factory=SourceSection
    )

    coding: CodingSection = field(
        default_factory=CodingSection
    )

    interleaving: InterleavingSection = field(
        default_factory=InterleavingSection
    )

    channel: ChannelSection = field(
        default_factory=ChannelSection
    )

    snr: SNRSection = field(
        default_factory=SNRSection
    )

    synchronization: SynchronizationSection = field(
        default_factory=SynchronizationSection
    )

    equalization: EqualizationSection = field(
        default_factory=EqualizationSection
    )

    papr: PAPRSection = field(
        default_factory=PAPRSection
    )

    metrics: MetricsSection = field(
        default_factory=MetricsSection
    )

    results: ResultsSection = field(
        default_factory=ResultsSection
    )

    visualization: VisualizationSection = field(
        default_factory=VisualizationSection
    )

    validation: ValidationSection = field(
        default_factory=ValidationSection
    )

    source_path: Optional[str] = None

    loaded_at_utc: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )

    raw: Dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # Derived configuration
    # ------------------------------------------------------------------

    def n_bits(self) -> int:
        """Return the resolved information-bit count."""
        return self.source.resolve_n_bits(
            data_subcarriers=self.ofdm.data_subcarriers,
            bits_per_symbol=self.modulation.bits_per_symbol,
            ofdm_blocks=self.simulation.effective_ofdm_blocks(),
        )

    def n_modulation_symbols(self) -> int:
        """Return the total number of mapped data symbols."""
        return int(
            self.ofdm.data_subcarriers
            * self.simulation.effective_ofdm_blocks()
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def to_config_snapshot(self) -> ConfigSnapshot:
        """
        Convert the high-level configuration into the compact core
        ``ConfigSnapshot`` representation.
        """
        return ConfigSnapshot(
            scenario_name=self.scenario.name,
            scenario_version=self.scenario.version,

            fft_size=self.ofdm.fft_size,
            active_subcarriers=self.ofdm.active_subcarriers,
            pilot_subcarriers=self.ofdm.pilot_subcarriers,
            data_subcarriers=self.ofdm.data_subcarriers,

            cyclic_prefix_length=self.ofdm.cyclic_prefix_length,
            oversampling_factor=self.ofdm.oversampling_factor,

            modulation=self.modulation.modulation_enum,
            channel=self.channel.channel_enum,

            snr_definition=self.channel.snr_definition_enum,

            papr_method=self.papr.papr_method_enum,

            coding=self.coding.coding_enum,
            interleaving=self.interleaving.interleaving_enum,

            random_seed=int(self.random.seed),

            ofdm_blocks=self.simulation.effective_ofdm_blocks(),

            fft_normalization=self.ofdm.fft_norm_enum,
            mapping_type=self.ofdm.mapping_enum,

            extra={
                "source_path": self.source_path,
                "loaded_at_utc": self.loaded_at_utc,
                "simulation_mode": self.simulation.mode,

                "papr_include_cp": self.papr.include_cp,

                "equalizer": self.equalization.method,
                "synchronization_enabled": (
                    self.synchronization.enabled
                ),
            },
        )

    # ------------------------------------------------------------------
    # Serialization / fingerprint
    # ------------------------------------------------------------------

    def to_plain_dict(
        self,
        *,
        include_raw: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert configuration into a JSON/YAML-compatible dictionary.
        """
        result: Dict[str, Any] = {
            "scenario": asdict(self.scenario),
            "random": asdict(self.random),
            "simulation": asdict(self.simulation),
            "ofdm": asdict(self.ofdm),
            "modulation": asdict(self.modulation),
            "source": asdict(self.source),
            "coding": asdict(self.coding),
            "interleaving": asdict(self.interleaving),
            "channel": asdict(self.channel),
            "snr": asdict(self.snr),
            "synchronization": asdict(self.synchronization),
            "equalization": asdict(self.equalization),
            "papr": asdict(self.papr),
            "metrics": asdict(self.metrics),
            "results": asdict(self.results),
            "visualization": asdict(self.visualization),
            "validation": asdict(self.validation),

            "source_path": self.source_path,
            "loaded_at_utc": self.loaded_at_utc,
        }

        if include_raw:
            result["raw"] = copy.deepcopy(
                self.raw
            )

        return result

    def fingerprint(self) -> str:
        """
        Return a deterministic SHA-256 configuration fingerprint.

        The timestamp and raw YAML representation are excluded so that
        equivalent configurations produce the same fingerprint.
        """
        payload = self.to_plain_dict(
            include_raw=False
        )

        payload.pop(
            "source_path",
            None,
        )

        payload.pop(
            "loaded_at_utc",
            None,
        )

        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Reference validation
    # ------------------------------------------------------------------

    def validate_reference_constraints(
        self,
    ) -> List[str]:
        """
        Validate locked reference-baseline constraints.

        Returns
        -------
        list[str]
            Human-readable violations.

        Raises
        ------
        ValueError
            When strict validation is enabled and one or more
            constraints are violated.
        """
        violations: List[str] = []

        validation = self.validation

        if not validation.enabled:
            return violations

        def add(
            condition: bool,
            message: str,
        ) -> None:
            if condition:
                violations.append(message)

        # --------------------------------------------------------------
        # Coding
        # --------------------------------------------------------------
        if validation.require_uncoded:
            coding_is_uncoded = (
                not self.coding.enabled
                and _normalize_enum_key(
                    self.coding.scheme
                ) in {"none", "off", ""}
            )

            add(
                not coding_is_uncoded,
                "Reference requires uncoded transmission.",
            )

        # --------------------------------------------------------------
        # Interleaving
        # --------------------------------------------------------------
        if validation.require_no_interleaving:
            interleaving_disabled = (
                not self.interleaving.enabled
                and _normalize_enum_key(
                    self.interleaving.type
                ) in {"none", "off", ""}
            )

            add(
                not interleaving_disabled,
                "Reference requires interleaving disabled.",
            )

        # --------------------------------------------------------------
        # Channel
        # --------------------------------------------------------------
        if validation.require_awgn:
            add(
                self.channel.channel_enum
                is not ChannelType.AWGN,
                "Reference requires AWGN channel.",
            )

        # --------------------------------------------------------------
        # Fading
        # --------------------------------------------------------------
        if validation.require_no_fading:
            fading_enabled = (
                self.channel.fading
                or self.channel.rayleigh_enabled
                or self.channel.rician_enabled
                or self.channel.channel_enum
                in {
                    ChannelType.RAYLEIGH,
                    ChannelType.RICIAN,
                }
            )

            add(
                fading_enabled,
                "Reference requires fading disabled.",
            )

        # --------------------------------------------------------------
        # Synchronization impairments
        # --------------------------------------------------------------
        if validation.require_no_synchronization_impairments:
            sync_enabled = (
                self.synchronization.enabled
                or self.synchronization.cfo_enabled
                or self.synchronization.timing_enabled
                or self.synchronization.phase_enabled
                or abs(
                    self.synchronization.cfo_normalized
                ) > 0.0
                or self.synchronization.timing_offset_samples != 0
                or abs(
                    self.synchronization.phase_radians
                ) > 0.0
            )

            add(
                sync_enabled,
                "Reference requires synchronization impairments disabled.",
            )

        # --------------------------------------------------------------
        # PAPR
        # --------------------------------------------------------------
        if validation.require_no_papr_reduction:
            add(
                self.papr.papr_method_enum
                is not PAPRMethod.NONE,
                "Reference requires PAPR method NONE.",
            )

        # --------------------------------------------------------------
        # Randomness
        # --------------------------------------------------------------
        if validation.require_fixed_seed:
            add(
                not isinstance(
                    self.random.seed,
                    int,
                ),
                "Reference requires a fixed integer random seed.",
            )

        if validation.require_reproducible_results:
            add(
                not self.random.deterministic
                or not self.random.centralized,
                "Reference requires deterministic centralized RNG.",
            )

        # --------------------------------------------------------------
        # Oversampling
        # --------------------------------------------------------------
        if validation.require_oversampling:
            add(
                self.ofdm.oversampling_factor < 2,
                "Reference requires oversampling_factor >= 2.",
            )

        # --------------------------------------------------------------
        # PAPR / CP
        # --------------------------------------------------------------
        if validation.require_cp_excluded_from_papr:
            add(
                self.papr.include_cp
                or self.ofdm.papr_include_cp,
                "Reference requires CP excluded from PAPR.",
            )

        # --------------------------------------------------------------
        # Strict mode
        # --------------------------------------------------------------
        if validation.strict and violations:
            raise ValueError(
                "Reference constraint violations:\n"
                + "\n".join(
                    f"  - {message}"
                    for message in violations
                )
            )

        return violations


# =============================================================================
# YAML helpers
# =============================================================================


def _require_yaml() -> None:
    """Ensure PyYAML is available."""
    if yaml is None:
        raise ImportError(
            "PyYAML is required to load configuration files. "
            "Install it with: pip install pyyaml"
        ) from _yaml_exc


def _as_dict(node: Any) -> Dict[str, Any]:
    """Convert a mapping-like node to a plain dictionary."""
    if node is None:
        return {}

    if isinstance(node, Mapping):
        return dict(node)

    raise TypeError(
        f"Expected mapping, got {type(node).__name__}."
    )


def _get(
    data: Mapping[str, Any],
    *keys: str,
    default: Any = None,
) -> Any:
    """
    Safely retrieve a nested configuration value.
    """
    current: Any = data

    for key in keys:
        if not isinstance(current, Mapping):
            return default

        if key not in current:
            return default

        current = current[key]

    return current


# =============================================================================
# Section parsers
# =============================================================================


def _parse_scenario(
    raw: Mapping[str, Any],
) -> ScenarioSection:
    section = _as_dict(
        _get(raw, "scenario", default={})
    )

    purpose = _get(
        section,
        "purpose",
        default=[],
    ) or []

    return ScenarioSection(
        name=str(
            _get(
                section,
                "name",
                default="reference_baseline",
            )
        ),
        version=str(
            _get(
                section,
                "version",
                default="1.1",
            )
        ),
        description=str(
            _get(
                section,
                "description",
                default="",
            )
            or ""
        ),
        status=str(
            _get(
                section,
                "status",
                default="locked",
            )
        ),
        reference=bool(
            _get(
                section,
                "reference",
                default=True,
            )
        ),
        purpose=tuple(
            str(item)
            for item in purpose
        ),
        papr_reduction=str(
            _get(
                section,
                "papr_reduction",
                default=_get(
                    raw,
                    "papr_reduction",
                    default="none",
                ),
            )
        ),
    )


def _parse_random(
    raw: Mapping[str, Any],
) -> RandomSection:
    section = _as_dict(
        _get(raw, "random", default={})
    )

    raw_streams = _get(
        section,
        "streams",
        default={},
    )

    streams = _as_dict(
        raw_streams
    )

    merged = dict(DEFAULT_STREAMS)

    for key, value in streams.items():
        merged[str(key)] = int(value)

    return RandomSection(
        seed=int(
            _get(
                section,
                "seed",
                default=DEFAULT_SEED,
            )
        ),
        deterministic=bool(
            _get(
                section,
                "deterministic",
                default=True,
            )
        ),
        centralized=bool(
            _get(
                section,
                "centralized",
                default=True,
            )
        ),
        streams=merged,
    )


def _parse_simulation(
    raw: Mapping[str, Any],
) -> SimulationSection:
    section = _as_dict(
        _get(raw, "simulation", default={})
    )

    return SimulationSection(
        mode=str(
            _get(
                section,
                "mode",
                default="research",
            )
        ),
        ofdm_blocks=int(
            _get(
                section,
                "ofdm_blocks",
                default=DEFAULT_OFDM_BLOCKS,
            )
        ),
        development_ofdm_blocks=int(
            _get(
                section,
                "development_ofdm_blocks",
                default=10_000,
            )
        ),
        monte_carlo_iterations=int(
            _get(
                section,
                "monte_carlo_iterations",
                default=1,
            )
        ),
        early_stopping=bool(
            _get(
                section,
                "early_stopping",
                default=False,
            )
        ),
    )


def _parse_ofdm(
    raw: Mapping[str, Any],
) -> OFDMSection:
    section = _as_dict(
        _get(raw, "ofdm", default={})
    )

    mapping = _as_dict(
        _get(
            section,
            "mapping",
            default={},
        )
    )

    return OFDMSection(
        fft_size=int(
            _get(
                section,
                "fft_size",
                default=DEFAULT_FFT_SIZE,
            )
        ),
        active_subcarriers=int(
            _get(
                section,
                "active_subcarriers",
                default=200,
            )
        ),
        pilot_subcarriers=int(
            _get(
                section,
                "pilot_subcarriers",
                default=8,
            )
        ),
        data_subcarriers=int(
            _get(
                section,
                "data_subcarriers",
                default=192,
            )
        ),
        cyclic_prefix_length=int(
            _get(
                section,
                "cyclic_prefix_length",
                default=DEFAULT_CP_LENGTH,
            )
        ),
        oversampling_factor=int(
            _get(
                section,
                "oversampling_factor",
                default=DEFAULT_OVERSAMPLING,
            )
        ),
        oversampling_method=str(
            _get(
                section,
                "oversampling_method",
                default="frequency_domain_zero_padding",
            )
        ),
        fft_normalization=str(
            _get(
                section,
                "fft_normalization",
                default="unitary",
            )
        ),
        dc_subcarrier=_get(
            section,
            "dc_subcarrier",
            default=None,
        ),
        guard_subcarriers=bool(
            _get(
                section,
                "guard_subcarriers",
                default=True,
            )
        ),
        mapping_type=str(
            _get(
                mapping,
                "type",
                default="symmetric",
            )
        ),
        include_dc=bool(
            _get(
                mapping,
                "include_dc",
                default=False,
            )
        ),
        papr_include_cp=bool(
            _get(
                section,
                "papr_include_cp",
                default=False,
            )
        ),
    )


def _parse_modulation(
    raw: Mapping[str, Any],
) -> ModulationSection:
    section = _as_dict(
        _get(raw, "modulation", default={})
    )

    return ModulationSection(
        scheme=str(
            _get(
                section,
                "scheme",
                default="QPSK",
            )
        ),
        order=int(
            _get(
                section,
                "order",
                default=4,
            )
        ),
        bits_per_symbol=int(
            _get(
                section,
                "bits_per_symbol",
                default=2,
            )
        ),
        mapping=str(
            _get(
                section,
                "mapping",
                default="gray",
            )
        ),
        normalize_average_power=bool(
            _get(
                section,
                "normalize_average_power",
                default=True,
            )
        ),
        target_average_symbol_energy=float(
            _get(
                section,
                "target_average_symbol_energy",
                default=1.0,
            )
        ),
    )


def _parse_source(
    raw: Mapping[str, Any],
) -> SourceSection:
    section = _as_dict(
        _get(raw, "source", default={})
    )

    alphabet = (
        _get(
            section,
            "binary_alphabet",
            default=[0, 1],
        )
        or [0, 1]
    )

    length = _get(
        section,
        "length",
        default="derived",
    )

    if isinstance(length, str):
        if length.strip().lower() == "derived":
            normalized_length: Union[str, int] = "derived"
        else:
            try:
                normalized_length = int(length)
            except ValueError as exc:
                raise ValueError(
                    "source.length must be 'derived' "
                    "or a positive integer."
                ) from exc
    else:
        normalized_length = int(length)

    return SourceSection(
        type=str(
            _get(
                section,
                "type",
                default="random_bits",
            )
        ),
        length=normalized_length,
        binary_alphabet=tuple(
            int(x)
            for x in alphabet
        ),
    )


def _parse_coding(
    raw: Mapping[str, Any],
) -> CodingSection:
    section = _as_dict(
        _get(raw, "coding", default={})
    )

    crc = _as_dict(
        _get(
            section,
            "crc",
            default={},
        )
    )

    return CodingSection(
        enabled=bool(
            _get(
                section,
                "enabled",
                default=False,
            )
        ),
        scheme=str(
            _get(
                section,
                "scheme",
                default="none",
            )
        ),
        code_rate=float(
            _get(
                section,
                "code_rate",
                default=1.0,
            )
        ),
        crc_enabled=bool(
            _get(
                crc,
                "enabled",
                default=False,
            )
        ),
        crc_width=int(
            _get(
                crc,
                "width",
                default=16,
            )
        ),
    )


def _parse_interleaving(
    raw: Mapping[str, Any],
) -> InterleavingSection:
    section = _as_dict(
        _get(raw, "interleaving", default={})
    )

    return InterleavingSection(
        enabled=bool(
            _get(
                section,
                "enabled",
                default=False,
            )
        ),
        type=str(
            _get(
                section,
                "type",
                default="none",
            )
        ),
        rows=_get(
            section,
            "rows",
            default=None,
        ),
        cols=_get(
            section,
            "cols",
            default=None,
        ),
    )


def _parse_channel(
    raw: Mapping[str, Any],
) -> ChannelSection:
    section = _as_dict(
        _get(raw, "channel", default={})
    )

    noise = _as_dict(
        _get(
            section,
            "noise",
            default={},
        )
    )

    rayleigh = _as_dict(
        _get(
            section,
            "rayleigh",
            default={},
        )
    )

    rician = _as_dict(
        _get(
            section,
            "rician",
            default={},
        )
    )

    return ChannelSection(
        model=str(
            _get(
                section,
                "model",
                default="AWGN",
            )
        ),
        enabled=bool(
            _get(
                section,
                "enabled",
                default=True,
            )
        ),
        fading=bool(
            _get(
                section,
                "fading",
                default=False,
            )
        ),
        snr_definition=str(
            _get(
                noise,
                "snr_definition",
                default=_get(
                    section,
                    "snr_definition",
                    default="EsN0",
                ),
            )
        ),
        rayleigh_enabled=bool(
            _get(
                rayleigh,
                "enabled",
                default=False,
            )
        ),
        rician_enabled=bool(
            _get(
                rician,
                "enabled",
                default=False,
            )
        ),
        rician_k_factor_db=float(
            _get(
                rician,
                "k_factor_db",
                default=3.0,
            )
        ),
        per_symbol_fading=bool(
            _get(
                section,
                "per_symbol_fading",
                default=True,
            )
        ),
    )


def _parse_snr(
    raw: Mapping[str, Any],
) -> SNRSection:
    section = _as_dict(
        _get(raw, "snr", default={})
    )

    raw_values = _get(
        section,
        "values",
        default=None,
    )

    if raw_values is None:
        values: Tuple[float, ...] = ()
    else:
        values = tuple(
            float(value)
            for value in raw_values
        )

    return SNRSection(
        start_db=float(
            _get(
                section,
                "start_db",
                default=0.0,
            )
        ),
        stop_db=float(
            _get(
                section,
                "stop_db",
                default=30.0,
            )
        ),
        step_db=float(
            _get(
                section,
                "step_db",
                default=2.0,
            )
        ),
        values=values,
    )


def _parse_synchronization(
    raw: Mapping[str, Any],
) -> SynchronizationSection:
    section = _as_dict(
        _get(
            raw,
            "synchronization",
            default={},
        )
    )

    cfo = _as_dict(
        _get(
            section,
            "carrier_frequency_offset",
            default={},
        )
    )

    timing = _as_dict(
        _get(
            section,
            "timing_offset",
            default={},
        )
    )

    phase = _as_dict(
        _get(
            section,
            "phase_offset",
            default={},
        )
    )

    return SynchronizationSection(
        enabled=bool(
            _get(
                section,
                "enabled",
                default=False,
            )
        ),
        cfo_enabled=bool(
            _get(
                cfo,
                "enabled",
                default=False,
            )
        ),
        cfo_normalized=float(
            _get(
                cfo,
                "normalized_offset",
                default=0.0,
            )
        ),
        timing_enabled=bool(
            _get(
                timing,
                "enabled",
                default=False,
            )
        ),
        timing_offset_samples=int(
            _get(
                timing,
                "sample_offset",
                default=0,
            )
        ),
        phase_enabled=bool(
            _get(
                phase,
                "enabled",
                default=False,
            )
        ),
        phase_radians=float(
            _get(
                phase,
                "radians",
                default=0.0,
            )
        ),
    )


def _parse_equalization(
    raw: Mapping[str, Any],
) -> EqualizationSection:
    section = _as_dict(
        _get(
            raw,
            "equalization",
            default={},
        )
    )

    return EqualizationSection(
        enabled=bool(
            _get(
                section,
                "enabled",
                default=False,
            )
        ),
        method=str(
            _get(
                section,
                "method",
                default="none",
            )
        ),
    )


def _parse_papr(
    raw: Mapping[str, Any],
) -> PAPRSection:
    section = _as_dict(
        _get(
            raw,
            "papr",
            default={},
        )
    )

    legacy_method = _get(
        raw,
        "papr_reduction",
        default=None,
    )

    method = _get(
        section,
        "method",
        default=(
            legacy_method
            if legacy_method is not None
            else "none"
        ),
    )

    probabilities = _get(
        section,
        "ccdf_probabilities",
        default=None,
    )

    if probabilities is None:
        probabilities = tuple(
            CCDF_REPORT_PROBABILITIES
        )

    return PAPRSection(
        method=str(method),
        include_cp=bool(
            _get(
                section,
                "include_cp",
                default=False,
            )
        ),
        ccdf_probabilities=tuple(
            float(value)
            for value in probabilities
        ),
        analysis_enabled=bool(
            _get(
                section,
                "analysis_enabled",
                default=True,
            )
        ),
    )


def _parse_metrics(
    raw: Mapping[str, Any],
) -> MetricsSection:
    ber = _as_dict(
        _get(raw, "ber", default={})
    )

    evm = _as_dict(
        _get(raw, "evm", default={})
    )

    psd = _as_dict(
        _get(raw, "psd", default={})
    )

    constellation = _as_dict(
        _get(
            raw,
            "constellation",
            default={},
        )
    )

    waveform = _as_dict(
        _get(
            raw,
            "waveform",
            default={},
        )
    )

    return MetricsSection(
        ber_enabled=bool(
            _get(
                ber,
                "enabled",
                default=True,
            )
        ),
        evm_enabled=bool(
            _get(
                evm,
                "enabled",
                default=True,
            )
        ),
        psd_enabled=bool(
            _get(
                psd,
                "enabled",
                default=True,
            )
        ),
        constellation_enabled=bool(
            _get(
                constellation,
                "enabled",
                default=True,
            )
        ),
        waveform_enabled=bool(
            _get(
                waveform,
                "enabled",
                default=True,
            )
        ),
        psd_method=str(
            _get(
                psd,
                "method",
                default="welch",
            )
        ),
        psd_window=str(
            _get(
                psd,
                "window",
                default="hann",
            )
        ),
        psd_nperseg=int(
            _get(
                psd,
                "nperseg",
                default=1024,
            )
        ),
        psd_noverlap=int(
            _get(
                psd,
                "noverlap",
                default=512,
            )
        ),
        diagnostic_samples=int(
            _get(
                waveform,
                "diagnostic_samples",
                default=4096,
            )
        ),
    )


def _parse_results(
    raw: Mapping[str, Any],
) -> ResultsSection:
    section = _as_dict(
        _get(
            raw,
            "results",
            default={},
        )
    )

    formats = _as_dict(
        _get(
            section,
            "formats",
            default={},
        )
    )

    directories = _as_dict(
        _get(
            section,
            "directories",
            default={},
        )
    )

    return ResultsSection(
        root_directory=str(
            _get(
                section,
                "root_directory",
                default="results/baseline",
            )
        ),
        overwrite=bool(
            _get(
                section,
                "overwrite",
                default=False,
            )
        ),
        save_raw_data=bool(
            _get(
                section,
                "save_raw_data",
                default=True,
            )
        ),
        save_processed_data=bool(
            _get(
                section,
                "save_processed_data",
                default=True,
            )
        ),
        save_configuration=bool(
            _get(
                section,
                "save_configuration",
                default=True,
            )
        ),
        save_metadata=bool(
            _get(
                section,
                "save_metadata",
                default=True,
            )
        ),
        save_summary=bool(
            _get(
                section,
                "save_summary",
                default=True,
            )
        ),
        csv=bool(
            _get(
                formats,
                "csv",
                default=True,
            )
        ),
        json=bool(
            _get(
                formats,
                "json",
                default=True,
            )
        ),
        numpy=bool(
            _get(
                formats,
                "numpy",
                default=True,
            )
        ),
        dir_papr=str(
            _get(
                directories,
                "papr",
                default="results/baseline/papr",
            )
        ),
        dir_ber=str(
            _get(
                directories,
                "ber",
                default="results/baseline/ber",
            )
        ),
        dir_evm=str(
            _get(
                directories,
                "evm",
                default="results/baseline/evm",
            )
        ),
        dir_psd=str(
            _get(
                directories,
                "psd",
                default="results/baseline/psd",
            )
        ),
        dir_figures=str(
            _get(
                directories,
                "figures",
                default="results/baseline/figures",
            )
        ),
        dir_metadata=str(
            _get(
                directories,
                "metadata",
                default="results/baseline/metadata",
            )
        ),
    )


def _parse_visualization(
    raw: Mapping[str, Any],
) -> VisualizationSection:
    section = _as_dict(
        _get(
            raw,
            "visualization",
            default={},
        )
    )

    figures = _as_dict(
        _get(
            section,
            "figures",
            default={},
        )
    )

    return VisualizationSection(
        enabled=bool(
            _get(
                section,
                "enabled",
                default=True,
            )
        ),
        style=str(
            _get(
                section,
                "style",
                default="scientific",
            )
        ),
        papr_ccdf=bool(
            _get(
                figures,
                "papr_ccdf",
                default=True,
            )
        ),
        ber_vs_snr=bool(
            _get(
                figures,
                "ber_vs_snr",
                default=True,
            )
        ),
        evm_vs_snr=bool(
            _get(
                figures,
                "evm_vs_snr",
                default=True,
            )
        ),
        constellation=bool(
            _get(
                figures,
                "constellation",
                default=True,
            )
        ),
        psd=bool(
            _get(
                figures,
                "psd",
                default=True,
            )
        ),
        waveform=bool(
            _get(
                figures,
                "waveform",
                default=True,
            )
        ),
        save_format=str(
            _get(
                section,
                "save_format",
                default="png",
            )
        ),
        dpi=int(
            _get(
                section,
                "dpi",
                default=300,
            )
        ),
        transparent=bool(
            _get(
                section,
                "transparent",
                default=False,
            )
        ),
        show_interactive=bool(
            _get(
                section,
                "show_interactive",
                default=False,
            )
        ),
    )


def _parse_validation(
    raw: Mapping[str, Any],
) -> ValidationSection:
    section = _as_dict(
        _get(
            raw,
            "validation",
            default={},
        )
    )

    constraints = _as_dict(
        _get(
            raw,
            "reference_constraints",
            default={},
        )
    )

    return ValidationSection(
        enabled=bool(
            _get(
                section,
                "enabled",
                default=True,
            )
        ),
        strict=bool(
            _get(
                section,
                "strict",
                default=True,
            )
        ),
        require_uncoded=bool(
            _get(
                constraints,
                "require_uncoded",
                default=True,
            )
        ),
        require_no_interleaving=bool(
            _get(
                constraints,
                "require_no_interleaving",
                default=True,
            )
        ),
        require_awgn=bool(
            _get(
                constraints,
                "require_awgn",
                default=True,
            )
        ),
        require_no_fading=bool(
            _get(
                constraints,
                "require_no_fading",
                default=True,
            )
        ),
        require_no_synchronization_impairments=bool(
            _get(
                constraints,
                "require_no_synchronization_impairments",
                default=True,
            )
        ),
        require_no_papr_reduction=bool(
            _get(
                constraints,
                "require_no_papr_reduction",
                default=True,
            )
        ),
        require_fixed_seed=bool(
            _get(
                constraints,
                "require_fixed_seed",
                default=True,
            )
        ),
        require_oversampling=bool(
            _get(
                constraints,
                "require_oversampling",
                default=True,
            )
        ),
        require_cp_excluded_from_papr=bool(
            _get(
                constraints,
                "require_cp_excluded_from_papr",
                default=True,
            )
        ),
        require_reproducible_results=bool(
            _get(
                constraints,
                "require_reproducible_results",
                default=True,
            )
        ),
    )


# =============================================================================
# Mapping → ExperimentConfig
# =============================================================================


def config_from_mapping(
    raw: Mapping[str, Any],
    *,
    source_path: Optional[str] = None,
    enforce_reference: bool = True,
) -> ExperimentConfig:
    """
    Build a fully typed ``ExperimentConfig`` from a mapping.

    Parameters
    ----------
    raw:
        Parsed YAML or equivalent mapping.

    source_path:
        Optional source-file path stored as metadata.

    enforce_reference:
        If True, strict reference constraints are enforced.

        If False, violations are returned as warnings rather than
        preventing configuration construction.
    """
    if not isinstance(raw, Mapping):
        raise TypeError(
            "Configuration root must be a mapping."
        )

    cfg = ExperimentConfig(
        scenario=_parse_scenario(raw),
        random=_parse_random(raw),
        simulation=_parse_simulation(raw),
        ofdm=_parse_ofdm(raw),
        modulation=_parse_modulation(raw),
        source=_parse_source(raw),
        coding=_parse_coding(raw),
        interleaving=_parse_interleaving(raw),
        channel=_parse_channel(raw),
        snr=_parse_snr(raw),
        synchronization=_parse_synchronization(raw),
        equalization=_parse_equalization(raw),
        papr=_parse_papr(raw),
        metrics=_parse_metrics(raw),
        results=_parse_results(raw),
        visualization=_parse_visualization(raw),
        validation=_parse_validation(raw),
        source_path=source_path,
        raw=copy.deepcopy(
            dict(raw)
        ),
    )

    # --------------------------------------------------------------
    # Reference validation
    # --------------------------------------------------------------
    if enforce_reference:
        cfg.validate_reference_constraints()

    else:
        strict_original = cfg.validation.strict

        try:
            cfg.validation.strict = False

            violations = (
                cfg.validate_reference_constraints()
            )

        finally:
            cfg.validation.strict = strict_original

        for message in violations:
            warnings.warn(
                message,
                UserWarning,
                stacklevel=2,
            )

    return cfg


# =============================================================================
# YAML loading
# =============================================================================


def load_yaml_file(
    path: PathLike,
) -> Dict[str, Any]:
    """
    Load a YAML configuration file.

    Parameters
    ----------
    path:
        Path to YAML file.

    Returns
    -------
    dict
        Parsed configuration mapping.
    """
    _require_yaml()

    path_obj = Path(path)

    if not path_obj.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {path_obj}"
        )

    text = path_obj.read_text(
        encoding="utf-8"
    )

    data = yaml.safe_load(text)

    if data is None:
        return {}

    if not isinstance(data, Mapping):
        raise TypeError(
            "YAML root must be a mapping, "
            f"got {type(data).__name__}."
        )

    return dict(data)


# =============================================================================
# High-level loaders
# =============================================================================


def load_config(
    path: Optional[PathLike] = None,
    *,
    overrides: Optional[Mapping[str, Any]] = None,
    enforce_reference: bool = True,
) -> ExperimentConfig:
    """
    Load an experiment configuration.

    Parameters
    ----------
    path:
        YAML configuration path.

        Defaults to ``configs/baseline.yaml``.

    overrides:
        Nested configuration overrides. Overrides are recursively
        merged into the YAML configuration.

    enforce_reference:
        Enforce locked baseline/reference constraints.

    Returns
    -------
    ExperimentConfig
        Fully resolved experiment configuration.
    """
    path_obj = (
        Path(path)
        if path is not None
        else default_baseline_path()
    )

    raw = load_yaml_file(
        path_obj
    )

    if overrides:
        raw = deep_merge(
            raw,
            dict(overrides),
        )

    return config_from_mapping(
        raw,
        source_path=str(
            path_obj.resolve()
        ),
        enforce_reference=enforce_reference,
    )


def load_baseline(
    *,
    development: bool = False,
    enforce_reference: bool = True,
) -> ExperimentConfig:
    """
    Load the canonical Stage-1 baseline configuration.

    ``development=True`` switches the simulation mode to development
    after the baseline configuration has been validated.
    """
    cfg = load_config(
        enforce_reference=enforce_reference
    )

    if development:
        cfg.simulation.mode = "development"

    return cfg


# =============================================================================
# Configuration manipulation
# =============================================================================


def deep_merge(
    base: Dict[str, Any],
    override: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Recursively merge configuration mappings.

    The original ``base`` mapping is never modified.
    """
    result = copy.deepcopy(base)

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], Mapping)
            and isinstance(value, Mapping)
        ):
            result[key] = deep_merge(
                dict(result[key]),
                value,
            )
        else:
            result[key] = copy.deepcopy(
                value
            )

    return result


# =============================================================================
# Configuration persistence
# =============================================================================


def save_config_json(
    cfg: ExperimentConfig,
    path: PathLike,
) -> Path:
    """
    Save the resolved configuration as JSON.
    """
    path_obj = Path(path)

    path_obj.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path_obj.write_text(
        json.dumps(
            cfg.to_plain_dict(
                include_raw=False
            ),
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return path_obj


def save_config_yaml(
    cfg: ExperimentConfig,
    path: PathLike,
) -> Path:
    """
    Save the resolved configuration as YAML.
    """
    _require_yaml()

    path_obj = Path(path)

    path_obj.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path_obj.open(
        "w",
        encoding="utf-8",
    ) as handle:
        yaml.safe_dump(
            cfg.to_plain_dict(
                include_raw=False
            ),
            handle,
            sort_keys=False,
            allow_unicode=True,
        )

    return path_obj


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "PathLike",

    "ScenarioSection",
    "RandomSection",
    "SimulationSection",
    "OFDMSection",
    "ModulationSection",
    "SourceSection",
    "CodingSection",
    "InterleavingSection",
    "ChannelSection",
    "SNRSection",
    "SynchronizationSection",
    "EqualizationSection",
    "PAPRSection",
    "MetricsSection",
    "ResultsSection",
    "VisualizationSection",
    "ValidationSection",

    "ExperimentConfig",

    "default_baseline_path",
    "default_configs_dir",

    "load_yaml_file",
    "load_config",
    "load_baseline",

    "config_from_mapping",
    "deep_merge",

    "save_config_json",
    "save_config_yaml",
]
