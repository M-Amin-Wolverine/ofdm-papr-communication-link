"""
Core public API for OFDM-PAPR-LinkSim
=====================================

The ``core`` package contains the stable architectural contracts and
pipeline orchestration primitives of OFDM-PAPR-LinkSim.

Public modules
--------------
types
    Canonical data contracts, validation rules, and result containers.

pipeline
    High-level simulation orchestration and dependency injection.

Design principles
-----------------
- ``core.types`` defines the canonical data model.
- ``core.pipeline`` consumes those contracts.
- Algorithm implementations live outside ``core``.
- Importing ``core`` must not execute simulation code.
- The public API is intentionally explicit.
"""

from __future__ import annotations

# =============================================================================
# Canonical data contracts
# =============================================================================

from .types import (
    BitArray,
    ComplexArray,
    ExperimentResult,
    PAPRResult,
    ReceiveFrame,
    SimulationMetadata,
    TransmitFrame,
)

# =============================================================================
# Pipeline orchestration
# =============================================================================

from .pipeline import (
    AnalyzerStage,
    BitsStage,
    GenericStage,
    ModulationStage,
    OFDMChain,
    OFDMDemodResultLike,
    PipelineComponents,
    PipelineContext,
    PipelineOptions,
)

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # -------------------------------------------------------------------------
    # Types / contracts
    # -------------------------------------------------------------------------
    "BitArray",
    "ComplexArray",
    "TransmitFrame",
    "ReceiveFrame",
    "PAPRResult",
    "SimulationMetadata",
    "ExperimentResult",

    # -------------------------------------------------------------------------
    # Pipeline
    # -------------------------------------------------------------------------
    "BitsStage",
    "ModulationStage",
    "GenericStage",
    "AnalyzerStage",
    "OFDMDemodResultLike",
    "PipelineContext",
    "PipelineComponents",
    "PipelineOptions",
    "OFDMChain",
]
