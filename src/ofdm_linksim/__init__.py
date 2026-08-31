"""
OFDM-PAPR-LinkSim
=================

A modular end-to-end OFDM communication-link simulator focused on
Peak-to-Average Power Ratio (PAPR) analysis and reduction research.

Package layout
--------------
core/
    types.py       Canonical data contracts (TransmitFrame, PAPRResult, …)
    pipeline.py    Orchestration engine (dependency-injected stages)
utils/
    random.py      Centralized reproducible RNG streams
    validation.py  Lightweight generic validators
analysis/
    ber.py, ccdf.py, evm.py, psd.py
blocks (this package root)
    source, modulation, ofdm_modulator, ofdm_demodulator,
    channel, papr, crc, channel_coding, channel_decoder,
    interleaver, equalizer, synchronization, config, output

Stage-1 baseline (locked)
-------------------------
- Uncoded QPSK
- AWGN channel
- No PAPR reduction (method = none)
- No interleaving / synchronization impairments
- PAPR measured on useful (non-CP) samples only
- Centralized deterministic RNG

Public import policy
--------------------
Importing ``ofdm_linksim`` must stay light: only stable, frequently used
symbols are re-exported here.  Heavy or optional pieces remain in their
submodules.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Mohammad Amin Khodadadi"
__license__ = "MIT"

# =============================================================================
# Core contracts
# =============================================================================

from ofdm_linksim.core.types import (
    # arrays / aliases
    RealArray,
    ComplexArray,
    BitArray,
    IntArray,
    # enums
    ModulationType,
    ChannelType,
    EqualizerType,
    PAPRMethod,
    CodingType,
    InterleavingType,
    FFTNormalization,
    SNRDefinition,
    MappingType,
    Units,
    # signal containers
    OFDMGrid,
    OFDMSignal,
    TransmitFrame,
    ReceiveFrame,
    ChannelOutput,
    # metrics
    PAPRResult,
    CCDFResult,
    PAPRStatistics,
    BERResult,
    EVMResult,
    PSDResult,
    ConstellationSnapshot,
    # config / experiment
    ConfigSnapshot,
    SimulationMetadata,
    ExperimentResult,
    # helpers
    validate_bits,
    validate_complex_signal,
    db_to_linear,
    linear_to_db,
    make_papr_result,
    compute_papr_linear,
    numpy_fft_norm,
    # defaults
    DEFAULT_FFT_SIZE,
    DEFAULT_OVERSAMPLING,
    DEFAULT_CP_LENGTH,
    DEFAULT_SEED,
    DEFAULT_OFDM_BLOCKS,
    CCDF_REPORT_PROBABILITIES,
)

from ofdm_linksim.core.pipeline import (
    OFDMChain,
    PipelineComponents,
    PipelineContext,
    PipelineOptions,
    AnalyzerStage,
    BitsStage,
    ModulationStage,
    GenericStage,
)

# =============================================================================
# Utilities
# =============================================================================

from ofdm_linksim.utils.random import (
    make_master_seed,
    make_rng,
    make_stream_rngs,
    source_rng,
    channel_rng,
    fading_rng,
    synchronization_rng,
    papr_rng,
    STREAM_SOURCE,
    STREAM_CHANNEL,
    STREAM_FADING,
    STREAM_SYNCHRONIZATION,
    STREAM_PAPR,
    DEFAULT_STREAMS,
)

from ofdm_linksim.utils.validation import (
    require_1d,
    require_same_length,
    require_finite,
    require_power_of_two,
    require_in_range,
)

# =============================================================================
# Analysis
# =============================================================================

from ofdm_linksim.analysis import (
    compute_ber,
    aggregate_ber,
    compute_evm,
    compute_ccdf,
    ccdf_at_probabilities,
    compute_psd,
)

# =============================================================================
# Transmit / receive blocks
# =============================================================================

from ofdm_linksim.source import (
    generate_random_bits,
    bits_from_bytes,
    bits_to_bytes,
)

from ofdm_linksim.modulation import (
    modulate,
    demodulate,
    bits_per_symbol,
    get_constellation,
    modulation_order,
)

from ofdm_linksim.ofdm_modulator import (
    modulate_ofdm,
    ofdm_modulator,
    map_symbols_to_grid,
    ofdm_ifft,
    add_cyclic_prefix,
    allocate_subcarriers,
)

from ofdm_linksim.ofdm_demodulator import (
    demodulate_ofdm,
    ofdm_demodulator,
    OFDMDemodResult,
    remove_cyclic_prefix,
    ofdm_fft,
)

from ofdm_linksim.channel import (
    apply_channel,
    apply_awgn,
    apply_rayleigh,
    apply_rician,
    channel,
)

from ofdm_linksim.papr import (
    compute_papr,
    papr_analysis,
    get_useful_samples,
    papr,
)

# Optional / identity Stage-1 blocks
from ofdm_linksim.crc import (
    encode_crc,
    check_crc,
    crc_encode,
    crc_decode,
)

from ofdm_linksim.channel_coding import (
    encode as channel_encode,
    encoder as channel_encoder,
)

from ofdm_linksim.channel_decoder import (
    decode as channel_decode,
    decoder as channel_decoder,
)

from ofdm_linksim.interleaver import (
    interleave,
    deinterleave,
    interleaver,
    deinterleaver,
)

from ofdm_linksim.equalizer import (
    equalize,
    equalizer,
)

from ofdm_linksim.synchronization import (
    apply_synchronization,
    synchronizer,
    synchronize,
)

# =============================================================================
# Configuration & output
# =============================================================================

from ofdm_linksim.config import (
    ExperimentConfig,
    load_config,
    load_baseline,
    load_yaml_file,
    config_from_mapping,
    default_baseline_path,
    save_config_json,
    save_config_yaml,
)

from ofdm_linksim.output import (
    ResultWriter,
    WriteReport,
    save_experiment,
    format_text_summary,
    write_ber_curve,
    write_evm_curve,
    append_summary_index,
)

# =============================================================================
# Public __all__
# =============================================================================

__all__ = [
    # package meta
    "__version__",
    "__author__",
    "__license__",
    # core types
    "RealArray",
    "ComplexArray",
    "BitArray",
    "IntArray",
    "ModulationType",
    "ChannelType",
    "EqualizerType",
    "PAPRMethod",
    "CodingType",
    "InterleavingType",
    "FFTNormalization",
    "SNRDefinition",
    "MappingType",
    "Units",
    "OFDMGrid",
    "OFDMSignal",
    "TransmitFrame",
    "ReceiveFrame",
    "ChannelOutput",
    "PAPRResult",
    "CCDFResult",
    "PAPRStatistics",
    "BERResult",
    "EVMResult",
    "PSDResult",
    "ConstellationSnapshot",
    "ConfigSnapshot",
    "SimulationMetadata",
    "ExperimentResult",
    "validate_bits",
    "validate_complex_signal",
    "db_to_linear",
    "linear_to_db",
    "make_papr_result",
    "compute_papr_linear",
    "numpy_fft_norm",
    "DEFAULT_FFT_SIZE",
    "DEFAULT_OVERSAMPLING",
    "DEFAULT_CP_LENGTH",
    "DEFAULT_SEED",
    "DEFAULT_OFDM_BLOCKS",
    "CCDF_REPORT_PROBABILITIES",
    # pipeline
    "OFDMChain",
    "PipelineComponents",
    "PipelineContext",
    "PipelineOptions",
    "AnalyzerStage",
    "BitsStage",
    "ModulationStage",
    "GenericStage",
    # utils
    "make_master_seed",
    "make_rng",
    "make_stream_rngs",
    "source_rng",
    "channel_rng",
    "fading_rng",
    "synchronization_rng",
    "papr_rng",
    "STREAM_SOURCE",
    "STREAM_CHANNEL",
    "STREAM_FADING",
    "STREAM_SYNCHRONIZATION",
    "STREAM_PAPR",
    "DEFAULT_STREAMS",
    "require_1d",
    "require_same_length",
    "require_finite",
    "require_power_of_two",
    "require_in_range",
    # analysis
    "compute_ber",
    "aggregate_ber",
    "compute_evm",
    "compute_ccdf",
    "ccdf_at_probabilities",
    "compute_psd",
    # blocks
    "generate_random_bits",
    "bits_from_bytes",
    "bits_to_bytes",
    "modulate",
    "demodulate",
    "bits_per_symbol",
    "get_constellation",
    "modulation_order",
    "modulate_ofdm",
    "ofdm_modulator",
    "map_symbols_to_grid",
    "ofdm_ifft",
    "add_cyclic_prefix",
    "allocate_subcarriers",
    "demodulate_ofdm",
    "ofdm_demodulator",
    "OFDMDemodResult",
    "remove_cyclic_prefix",
    "ofdm_fft",
    "apply_channel",
    "apply_awgn",
    "apply_rayleigh",
    "apply_rician",
    "channel",
    "compute_papr",
    "papr_analysis",
    "get_useful_samples",
    "papr",
    "encode_crc",
    "check_crc",
    "crc_encode",
    "crc_decode",
    "channel_encode",
    "channel_encoder",
    "channel_decode",
    "channel_decoder",
    "interleave",
    "deinterleave",
    "interleaver",
    "deinterleaver",
    "equalize",
    "equalizer",
    "apply_synchronization",
    "synchronizer",
    "synchronize",
    # config / output
    "ExperimentConfig",
    "load_config",
    "load_baseline",
    "load_yaml_file",
    "config_from_mapping",
    "default_baseline_path",
    "save_config_json",
    "save_config_yaml",
    "ResultWriter",
    "WriteReport",
    "save_experiment",
    "format_text_summary",
    "write_ber_curve",
    "write_evm_curve",
    "append_summary_index",
]


def get_version() -> str:
    """Return the package version string."""
    return __version__


def stage1_baseline_summary() -> Dict[str, str]:
    """Short textual description of the locked Stage-1 scientific baseline."""
    return {
        "modulation": "QPSK",
        "channel": "AWGN",
        "coding": "none",
        "interleaving": "none",
        "papr_method": "none",
        "equalizer": "none",
        "synchronization_impairments": "disabled",
        "papr_cp_policy": "excluded",
        "rng": "centralized deterministic streams",
        "version": __version__,
    }


# late import for typing in stage1_baseline_summary
from typing import Dict  # noqa: E402
