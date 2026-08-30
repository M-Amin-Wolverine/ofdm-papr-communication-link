"""
Utility helpers for OFDM-PAPR-LinkSim
=====================================

- random : centralized, reproducible random streams
- validation : lightweight general-purpose checks
"""

from __future__ import annotations

from .random import (
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

from .validation import (
    require_1d,
    require_same_length,
    require_finite,
    require_power_of_two,
    require_in_range,
)

__all__ = [
    # random
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
    # validation
    "require_1d",
    "require_same_length",
    "require_finite",
    "require_power_of_two",
    "require_in_range",
]
