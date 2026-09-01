import numpy as np
import pytest

from ofdm_linksim.papr import compute_papr, get_useful_samples
from ofdm_linksim.core.types import PAPRMethod
from ofdm_linksim.utils.random import make_stream_rngs


def test_get_useful_samples_excludes_cp():
    # dummy waveform با CP
    n_fft = 256
    n_cp = 16
    n_total = n_fft + n_cp
    waveform = np.random.randn(n_total) + 1j * np.random.randn(n_total)

    useful = get_useful_samples(waveform)
    assert useful.size == n_fft * 4  # oversampling=4
    assert useful.size < n_total  # CP حذف شده


def test_compute_papr_on_useful_samples():
    samples = np.random.randn(256 * 4)
    pr = compute_papr(samples)
    assert pr.papr_linear >= 1.0
    assert 0 <= pr.papr_db <= 100
