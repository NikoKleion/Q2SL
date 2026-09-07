# suite.zx_fingerprint: decide gate-identity of two circuits with ZX-calculus (needs pyzx).
import hashlib

try:
    import numpy as np
    import pyzx as zx
    from pyzx.circuit import Circuit
    _HAVE = True
except Exception:
    _HAVE = False


def _require():
    if not _HAVE:
        raise RuntimeError("zx_fingerprint requires pyzx (pip install pyzx)")


def zx_equivalent(c1, c2):
    # ZX equality: reduce c1 . c2-adjoint and check it is the identity diagram.
    _require()
    return bool(c1.verify_equality(c2))


def fingerprint(c):
    # canonical key that collides for gate-identity-equal circuits: ZX-reduce, then hash the phase-normalized tensor (small circuits only).
    _require()
    g = c.to_graph(); zx.simplify.full_reduce(g)
    t = g.to_tensor().ravel()
    nz = t[np.abs(t) > 1e-9]
    if len(nz):
        t = t * np.conj(nz[0]) / abs(nz[0])
    q = np.round(np.stack([t.real, t.imag]), 6).tobytes()
    return hashlib.sha1(q).hexdigest()[:12]


def _cnot():
    c = Circuit(2); c.add_gate("CNOT", 0, 1); return c


def _cnot_obfuscated():
    # CNOT = (I x H) . CZ . (I x H): a different gate list that is the same operation
    c = Circuit(2)
    c.add_gate("HAD", 1); c.add_gate("CZ", 0, 1); c.add_gate("HAD", 1)
    return c


def _cnot_padded():
    # three CNOTs collapse to one CNOT; also a redundant S . S-dagger identity on qubit 0
    c = Circuit(2)
    c.add_gate("S", 0); c.add_gate("CNOT", 0, 1); c.add_gate("CNOT", 0, 1)
    c.add_gate("CNOT", 0, 1); c.add_gate("S", 0, adjoint=True)
    return c


def _cz():
    c = Circuit(2); c.add_gate("CZ", 0, 1); return c


def _swap():
    c = Circuit(2)
    for _ in range(3):
        c.add_gate("CNOT", 0, 1); c.add_gate("CNOT", 1, 0)
    return c


def main():
    _require()
    lib = {"CNOT": _cnot(), "CNOT_obfuscated": _cnot_obfuscated(),
           "CNOT_padded": _cnot_padded(), "CZ": _cz(), "SWAP-ish": _swap()}
    print("# ZX gate-identity: fingerprint COLLIDES exactly when two circuits are the same operation.\n")
    print(f"#   {'circuit':>16}  {'gates':>5}  fingerprint")
    fps = {}
    for name, c in lib.items():
        fp = fingerprint(c); fps[name] = fp
        print(f"#   {name:>16}  {len(c.gates):>5}  {fp}")
    ref = fps["CNOT"]
    print(f"\n#   which circuits ZX-equal the plain CNOT (fingerprint {ref})?")
    for name, c in lib.items():
        eq = zx_equivalent(lib["CNOT"], c)
        mark = "SAME operation" if eq else "different"
        collide = "collide" if fps[name] == ref else "distinct"
        print(f"#   {name:>16}: ZX says {mark:>14}   (fingerprint {collide})")
    print("\n#   the two obfuscated CNOTs are unmasked as CNOT; CZ and SWAP stay distinct. An adversary or auditor")
    print("#   who sees the compiled circuit recovers WHICH operation it is, regardless of how it was written.")


if __name__ == "__main__":
    main()
