# structure run: leak order across codes built through the strings-only CSS path, past the projector ceiling
import numpy as np

import syndrome_leakage as sl
from syndrome_leakage.analyze import analytic_leak
from syndrome_leakage.css import css_strings, code_distance


def _order(code):
    leaks, o = analytic_leak(code)
    return o if leaks else None


def _hamming_H(r):
    ncol = 2 ** r - 1
    return np.array([[(col >> (r - 1 - bit)) & 1 for bit in range(r)] for col in range(1, ncol + 1)], np.uint8).T


def test_same_nkd_different_leak():
    # two [[7,1,3]] codes: asymmetric leaks, balanced protected
    assert _order(sl.codes.STANDARD["hamming_7"]()) == 3
    assert _order(sl.codes.STANDARD["steane"]()) is None


def test_self_dual_hamming_css_is_protected():
    H = _hamming_H(3)
    sc = css_strings(H, H, "Hamming-CSS[[7,1,3]]")
    assert code_distance(H, H) == 3
    assert _order(sc) is None


def test_string_path_reaches_shor_and_it_leaks():
    Hx = np.array([[1, 1, 1, 1, 1, 1, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1]], np.uint8)
    Hz = np.array([[1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 1, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1]], np.uint8)
    shor = css_strings(Hx, Hz, "Shor[[9,1,3]]")
    assert code_distance(Hx, Hz) == 3
    assert _order(shor) == 3
