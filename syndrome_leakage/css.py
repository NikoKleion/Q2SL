# Build a Code from CSS parity-check matrices via GF(2) homology.
import numpy as np
from .core import Code


def _rref(M):
    # reduced row echelon form over GF(2); returns (R, pivot_columns)
    R = (np.asarray(M) % 2).astype(np.uint8).copy()
    rows, cols = R.shape
    piv, r = [], 0
    for c in range(cols):
        pr = next((i for i in range(r, rows) if R[i, c]), None)
        if pr is None:
            continue
        R[[r, pr]] = R[[pr, r]]
        for i in range(rows):
            if i != r and R[i, c]:
                R[i] ^= R[r]
        piv.append(c); r += 1
        if r == rows:
            break
    return R, piv


def _rank(M):
    return len(_rref(M)[1])


def _kernel(M):
    # basis of the right null space of M over GF(2)
    M = (np.asarray(M) % 2).astype(np.uint8)
    if M.size == 0:
        return np.eye(M.shape[1], dtype=np.uint8) if M.shape[1] else np.zeros((0, 0), np.uint8)
    R, piv = _rref(M)
    cols = M.shape[1]
    free = [c for c in range(cols) if c not in piv]
    basis = []
    for f in free:
        v = np.zeros(cols, np.uint8); v[f] = 1
        for i, p in enumerate(piv):
            if R[i, f]:
                v[p] = 1
        basis.append(v)
    return np.array(basis, np.uint8) if basis else np.zeros((0, cols), np.uint8)


def _in_rowspace(v, basis):
    # is v in the GF(2) row space of basis?
    if len(basis) == 0:
        return not np.any(v % 2)
    stack = np.vstack([np.asarray(basis) % 2, (np.asarray(v) % 2)[None, :]])
    return _rank(stack) == _rank(basis)


def _logical_reps(Hx, Hz):
    # logical X reps = ker(Hz) not in rowspace(Hx); logical Z reps = ker(Hx) not in rowspace(Hz)
    kx = [v for v in _kernel(Hz) if not _in_rowspace(v, Hx)]
    kz = [v for v in _kernel(Hx) if not _in_rowspace(v, Hz)]
    return kx, kz


def _to_str(vec, sym):
    return "".join(sym if b else "I" for b in np.asarray(vec) % 2)


def css_from_matrices(Hx, Hz, name="CSS"):
    # build a one-logical-qubit Code from CSS check matrices; requires Hx Hz^T = 0 and k=1
    Hx = (np.asarray(Hx) % 2).astype(np.uint8)
    Hz = (np.asarray(Hz) % 2).astype(np.uint8)
    assert Hx.shape[1] == Hz.shape[1], "Hx and Hz must have the same number of qubits (columns)"
    n = Hx.shape[1]
    assert not np.any((Hx @ Hz.T) % 2), "CSS condition Hx Hz^T = 0 violated (stabilizers do not commute)"
    k = n - _rank(Hx) - _rank(Hz)
    assert k == 1, f"this backend targets one logical qubit; got k={k}. Trim the code or pick a logical pair."
    kx, kz = _logical_reps(Hx, Hz)
    assert kx and kz, "no logical operators found"
    for zc in kz:
        for xc in kx:
            if int(np.dot(zc, xc)) % 2 == 1:
                stabs = [_to_str(r, "X") for r in Hx if np.any(r)] + [_to_str(r, "Z") for r in Hz if np.any(r)]
                return Code(name, n, stabs, _to_str(zc, "Z"), _to_str(xc, "X"))
    raise AssertionError("could not find an anticommuting logical X/Z pair")


class _StringCode:
    # strings-only code carrier for the analytic path; no density matrix, so no projector ceiling
    def __init__(self, name, n, stab_strings, zl_str, xl_str):
        self.name = name
        self.n = n
        self.stab_strings = list(stab_strings)
        self.zl_str = zl_str
        self.xl_str = xl_str


def _min_coset_weight(rep, basis):
    # minimum Hamming weight of rep + span(basis) over GF(2); basis is small (2^rank enumeration)
    rep = np.asarray(rep) % 2
    rows = [np.asarray(b) % 2 for b in basis]
    m = len(rows)
    best = int(np.count_nonzero(rep))
    for mask in range(1, 1 << m):
        v = rep.copy()
        for i in range(m):
            if (mask >> i) & 1:
                v = (v + rows[i]) % 2
        w = int(np.count_nonzero(v))
        if w < best:
            best = w
    return best


def code_distance(Hx, Hz):
    # min weight of a nontrivial logical operator (X or Z coset), for verifying a constructed code
    Hx = (np.asarray(Hx) % 2).astype(np.uint8)
    Hz = (np.asarray(Hz) % 2).astype(np.uint8)
    kx, kz = _logical_reps(Hx, Hz)
    dz = min(_min_coset_weight(z, Hz) for z in kz)
    dx = min(_min_coset_weight(x, Hx) for x in kx)
    return min(dx, dz)


def css_strings(Hx, Hz, name="CSS"):
    # same construction and GF(2) verification as css_from_matrices, returning strings only (no Code).
    Hx = (np.asarray(Hx) % 2).astype(np.uint8)
    Hz = (np.asarray(Hz) % 2).astype(np.uint8)
    assert Hx.shape[1] == Hz.shape[1], "Hx and Hz must have the same number of qubits (columns)"
    n = Hx.shape[1]
    assert not np.any((Hx @ Hz.T) % 2), "CSS condition Hx Hz^T = 0 violated"
    k = n - _rank(Hx) - _rank(Hz)
    assert k == 1, f"this backend targets one logical qubit; got k={k}"
    kx, kz = _logical_reps(Hx, Hz)
    assert kx and kz, "no logical operators found"
    for zc in kz:
        for xc in kx:
            if int(np.dot(zc, xc)) % 2 == 1:
                stabs = [_to_str(r, "X") for r in Hx if np.any(r)] + [_to_str(r, "Z") for r in Hz if np.any(r)]
                return _StringCode(name, n, stabs, _to_str(zc, "Z"), _to_str(xc, "X"))
    raise AssertionError("could not find an anticommuting logical X/Z pair")


def hamming_css(r=3):
    # [[2^r-1, 1, 3]] quantum Hamming code from the classical Hamming check matrix, Hx=Hz=H
    ncol = 2 ** r - 1
    H = np.array([[(col >> (r - 1 - bit)) & 1 for bit in range(r)] for col in range(1, ncol + 1)], np.uint8).T
    return css_from_matrices(H, H, name=f"Hamming-CSS[[{ncol},1,3]] (r={r})")
