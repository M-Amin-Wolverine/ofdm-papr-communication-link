"""
Centralized random-number management
====================================

All stochastic processes in OFDM-PAPR-LinkSim MUST obtain their
Generator from this module.  Direct calls to ``np.random.seed()``
or the global ``np.random`` module are forbidden.

Design rules (locked)
---------------------
1. A single master seed is owned by the pipeline invocation.
2. Named streams are derived deterministically from the master seed.
3. Each stream receives an independent ``np.random.Generator``.
4. The same (seed, stream_id) pair always produces the identical sequence.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

# Canonical stream identifiers used throughout the project
# (must stay consistent with configs/baseline.yaml and core.types)
STREAM_SOURCE: int = 1
STREAM_CHANNEL: int = 2
STREAM_FADING: int = 3
STREAM_SYNCHRONIZATION: int = 4
STREAM_PAPR: int = 5

DEFAULT_STREAMS: Dict[str, int] = {
    "source": STREAM_SOURCE,
    "channel": STREAM_CHANNEL,
    "fading": STREAM_FADING,
    "synchronization": STREAM_SYNCHRONIZATION,
    "papr": STREAM_PAPR,
}


def make_master_seed(seed: int) -> int:
    """
    Validate and normalise the master seed.

    Parameters
    ----------
    seed :
        Non-negative integer supplied by the user / configuration.

    Returns
    -------
    int
        The same seed (after validation).
    """
    if not isinstance(seed, (int, np.integer)):
        raise TypeError(f"seed must be an integer, got {type(seed)}")
    seed = int(seed)
    if seed < 0:
        raise ValueError(f"seed must be non-negative, got {seed}")
    return seed


def make_rng(
    master_seed: int,
    stream_id: int,
) -> np.random.Generator:
    """
    Create an independent Generator for a given stream.

    The derivation is deterministic:
        child_seed = (master_seed + stream_id * large_prime) mod 2**32

    This guarantees that different streams never share state
    while remaining fully reproducible.

    Parameters
    ----------
    master_seed :
        Central experiment seed.
    stream_id :
        Positive integer identifying the stream
        (see STREAM_* constants or DEFAULT_STREAMS).

    Returns
    -------
    np.random.Generator
    """
    master_seed = make_master_seed(master_seed)

    if not isinstance(stream_id, (int, np.integer)):
        raise TypeError(f"stream_id must be an integer, got {type(stream_id)}")
    stream_id = int(stream_id)
    if stream_id < 0:
        raise ValueError(f"stream_id must be non-negative, got {stream_id}")

    # Simple, fast, deterministic mixing (good enough for research reproducibility)
    # Using a large odd constant to reduce correlation between adjacent streams.
    child_seed = (master_seed + stream_id * 0x9E3779B9) & 0xFFFFFFFF
    return np.random.default_rng(child_seed)


def make_stream_rngs(
    master_seed: int,
    streams: Optional[Dict[str, int]] = None,
) -> Dict[str, np.random.Generator]:
    """
    Create a dictionary of named Generators in one call.

    Parameters
    ----------
    master_seed :
        Central experiment seed.
    streams :
        Mapping from stream name → stream_id.
        Defaults to the project-wide DEFAULT_STREAMS.

    Returns
    -------
    dict[str, np.random.Generator]
    """
    if streams is None:
        streams = DEFAULT_STREAMS

    master_seed = make_master_seed(master_seed)
    return {
        name: make_rng(master_seed, stream_id)
        for name, stream_id in streams.items()
    }


# Convenience aliases that match the configuration language
def source_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_SOURCE)


def channel_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_CHANNEL)


def fading_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_FADING)


def synchronization_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_SYNCHRONIZATION)


def papr_rng(master_seed: int) -> np.random.Generator:
    return make_rng(master_seed, STREAM_PAPR)
