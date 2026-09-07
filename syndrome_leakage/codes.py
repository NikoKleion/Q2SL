# Standard stabilizer code library; each constructor returns a Code.
import numpy as np
from .core import Code


def _toric_hz_strings(L):
    n = 2 * L * L
    Hh = lambda r, c: (r % L) * L + (c % L)
    Vt = lambda r, c: L * L + (r % L) * L + (c % L)
    out = []
    for r in range(L):
        for c in range(L):
            row = ["I"] * n
            for idx in (Hh(r, c), Hh(r + 1, c), Vt(r, c), Vt(r, c + 1)):
                row[idx] = "Z"
            out.append("".join(row))
    return out


def repetition():
    # 3-qubit bit-flip code; weight-1 logical Z, leaks population at O(gamma)
    return Code("3-qubit repetition", 3, ["ZZI", "IZZ"], "ZII", "XXX")


def five_qubit():
    # perfect [[5,1,3]] code; balanced, so amplitude damping leaks nothing
    return Code("5-qubit [[5,1,3]]", 5, ["XZZXI", "IXZZX", "XIXZZ", "ZXIXZ"], "ZZZZZ", "XXXXX")


def steane():
    # [[7,1,3]] CSS code, protected under amplitude damping
    return Code("Steane [[7,1,3]]", 7,
                ["IIIXXXX", "IXXIIXX", "XIXIXIX", "IIIZZZZ", "IZZIIZZ", "ZIZIZIZ"], "ZZZZZZZ", "XXXXXXX")


def code_4_1_2():
    # distance-2 code, one-body balanced but leaks at O(gamma^2)
    return Code("[[4,1,2]]", 4, ["XXXX", "ZZII", "IIZZ"], "ZIZI", "XXII")


def hamming_7():
    # CSS code with Hamming[7,4,3] Z-side; first leak is 3-body, so O(gamma^3)
    return Code("Hamming [[7,1,3]]", 7,
                ["XIXIXIX", "IXXIIXX", "IIIXXXX", "ZZZZZZZ", "ZIIZZII", "IZIZIZI"], "IIZIZZI", "XXXIXXX")


STANDARD = {
    "repetition": repetition,
    "five_qubit": five_qubit,
    "steane": steane,
    "code_4_1_2": code_4_1_2,
    "hamming_7": hamming_7,
}
