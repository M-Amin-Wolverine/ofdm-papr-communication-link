"""
Bit Error Rate (BER) analysis
=============================

Pure measurement functions that produce ``BERResult`` objects
defined in ``core.types``.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from ofdm_linksim.core.types import (
    BitArray,
    BERResult,
    validate_bits,
)


def compute_ber(
    tx_bits: BitArray,
    rx_bits: BitArray,
    *,
    snr_db: Optional[float] = None,
) -> BERResult:
    """
    Compute bit error rate between transmitted and received bit sequences.

    Parameters
    ----------
    tx_bits :
        Original transmitted bits (1-D, values in {0, 1}).
    rx_bits :
        Recovered bits after the complete receiver chain.
        Must have the same length as ``tx_bits``.
    snr_db :
        Optional SNR at which this measurement was taken.
        Stored for later plotting / aggregation.

    Returns
    -------
    BERResult
        Frozen result container with bit_errors, total_bits, ber and snr_db.
    """
    validate_bits(tx_bits)
    validate_bits(rx_bits)

    tx = np.asarray(tx_bits, dtype=np.uint8).ravel()
    rx = np.asarray(rx_bits, dtype=np.uint8).ravel()

    if tx.size != rx.size:
        raise ValueError(
            f"tx_bits and rx_bits length mismatch: "
            f"{tx.size} vs {rx.size}"
        )

    if tx.size == 0:
        raise ValueError("Cannot compute BER on empty bit arrays.")

    bit_errors = int(np.sum(tx != rx))
    total_bits = int(tx.size)
    ber = bit_errors / total_bits

    return BERResult(
        bit_errors=bit_errors,
        total_bits=total_bits,
        ber=ber,
        snr_db=snr_db,
    )


def aggregate_ber(results: list[BERResult]) -> BERResult:
    """
    Aggregate several independent BER measurements
    (useful for Monte-Carlo over many blocks or SNR points).
    """
    if not results:
        raise ValueError("Cannot aggregate empty list of BERResult.")

    total_errors = sum(r.bit_errors for r in results)
    total_bits = sum(r.total_bits for r in results)
    ber = total_errors / total_bits if total_bits > 0 else 0.0

    # Keep SNR only if all measurements share the same SNR
    snrs = {r.snr_db for r in results}
    snr_db = snrs.pop() if len(snrs) == 1 else None

    return BERResult(
        bit_errors=total_errors,
        total_bits=total_bits,
        ber=ber,
        snr_db=snr_db,
    )
