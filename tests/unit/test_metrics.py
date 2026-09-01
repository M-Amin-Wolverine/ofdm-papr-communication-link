import numpy as np
import pytest

from ofdm_linksim.analysis.ber import compute_ber
from ofdm_linksim.analysis.evm import compute_evm
from ofdm_linksim.analysis.ccdf import compute_ccdf


def test_compute_ber():
    tx = np.array([0, 1, 0, 1])
    rx = np.array([0, 1, 0, 1])
    ber = compute_ber(tx, rx, snr_db=20.0)
    assert 0 <= ber.ber <= 1
    assert ber.bit_errors == 0
    assert ber.total_bits == 4


def test_compute_evm():
    tx = np.random.randn(100) + 1j * np.random.randn(100)
    rx = tx + 0.01 * (np.random.randn(100) + 1j * np.random.randn(100))
    evm = compute_evm(tx, rx)
    assert evm.rms_evm >= 0


def test_compute_ccdf():
    papr_db = np.random.randn(100) + 10
    ccdf = compute_ccdf(papr_db)
    assert len(ccdf.thresholds_db) == 50
    assert all(0 <= x <= 1 for x in ccdf.probabilities)
