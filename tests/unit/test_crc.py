import numpy as np
import pytest

from ofdm_linksim.crc import encode_crc, check_crc


def test_crc_encode_check():
    data = np.array([1, 0, 1, 1], dtype=bool)
    crc32 = encode_crc(data)
    assert len(crc32) == 32
    assert check_crc(data, crc32) is True
