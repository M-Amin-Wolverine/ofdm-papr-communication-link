import numpy as np
import pytest

from ofdm_linksim.synchronization import apply_synchronization
from ofdm_linksim.core.types import SynchronizationType


def test_synchronization_none():
    waveform = np.random.randn(1000) + 1j * np.random.randn(1000)
    synced, meta = apply_synchronization(waveform, scheme=SynchronizationType.NONE)
    assert np.array_equal(synced, waveform)
