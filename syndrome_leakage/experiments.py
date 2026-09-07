# Every documented run, as one command each. Writes to results/ when given --save.
import math
import sys

import numpy as np

from . import codes as _codes
from .analyze import analytic_leak, population_leak, selftest as _selftest
from .channels import (amplitude_damping, channel_from_t1t2, coherent_diagonal, dephasing,
                       depolarizing)
from .core import tvd
from .css import code_distance, css_strings
from .eavesdrop import (bhattacharyya_coefficient, chernoff_exponent, ml_attack, repeated_extraction,
                        rounds_for_error, state_grid, worst_case_pair)
from .kl_check import ad_population_distance

STD = _codes.STANDARD
MARRAKESH = (163.3e-6, 77.0e-6, 1e-6)  # median T1, median T2, syndrome cycle


def _order(code):
    leaks, o = analytic_leak(code)
    return o if leaks else None


def selftest():
    # analytic leak order against the exact simulation, every standard code
    _selftest()


def attack(trials=200000):
    # achieved eavesdropper error against the two closed-form bounds
    c = STD["hamming_7"]()
    leak, d0, d1 = population_leak(c, amplitude_damping(0.2))
    C, s = chernoff_exponent(d0, d1)
    print(f"Hamming [[7,1,3]], amplitude_damping(0.2), {trials} trials")
    print(f"syndrome TVD {leak:.4e}, Chernoff {C:.6f} nats at s*={s:.3f}, "
          f"Bhattacharyya coefficient {bhattacharyya_coefficient(d0, d1):.6f}")
    print()
    print("  rounds   ML attack error      Chernoff rate   Bhattacharyya bound")
    for r in (1, 10, 50, 200):
        e = ml_attack(d0, d1, r, trials=trials, seed=r)
        se = math.sqrt(max(e * (1 - e), 1e-12) / trials)
        print(f"  {r:6d}   {e:.4f} +/- {se:.4f}     {0.5 * math.exp(-C * r):13.4f}   "
              f"{0.5 * bhattacharyya_coefficient(d0, d1) ** r:19.4f}")
    print()
    print(f"one-shot closed form (1 - TVD)/2 = {0.5 * (1 - leak):.4f}")
    print("rounds to 1 percent error, by code and gamma:")
    for g in (0.1, 0.2, 0.3):
        row = []
        for name in ("repetition", "code_4_1_2", "hamming_7"):
            _l, a, b = population_leak(STD[name](), amplitude_damping(g))
            row.append(f"{name} {rounds_for_error(a, b, 0.01)}")
        print(f"  gamma={g}: " + ", ".join(row))


def leak_order():
    # analytic leak order against the codeword amplitude-damping population distance
    print("code                       analytic order   AD population distance   match")
    for name in STD:
        c = STD[name]()
        a, k = _order(c), ad_population_distance(c)
        print(f"  {c.name:24} {str(a):>14}   {str(k):>22}   {'yes' if a == k else 'NO'}")


def coherent(theta=0.3):
    # coherent diagonal noise: which codes leak, how it scales, Pauli controls
    print(f"coherent_diagonal(theta={theta}), population TVD by code")
    for name in STD:
        leak, _, _ = population_leak(STD[name](), coherent_diagonal(theta))
        print(f"  {name:12} {leak:.4e}")
    c = STD["code_4_1_2"]()
    print("\n[[4,1,2]] scaling in theta")
    for t in (0.05, 0.1, 0.2, 0.3):
        leak, _, _ = population_leak(c, coherent_diagonal(t))
        print(f"  theta={t:.2f}  TVD {leak:.4e}  TVD/theta^2 {leak / t ** 2:.3f}")
    print("\nPauli controls on [[4,1,2]] (must be 0)")
    for nm, K in (("dephasing(0.1)", dephasing(0.1)), ("depolarizing(0.1)", depolarizing(0.1))):
        leak, _, _ = population_leak(c, K)
        print(f"  {nm}: {leak:.2e}")
    leak, d0, d1 = population_leak(c, coherent_diagonal(0.2))
    C, _s = chernoff_exponent(d0, d1)
    print(f"\nattack at theta=0.2: TVD {leak:.4e}, Chernoff {C:.4f} nats, "
          f"rounds to 1 percent {rounds_for_error(d0, d1, 0.01)}")


def structure():
    # the leak is a structural property, not an [[n,k,d]] invariant
    print("same [[7,1,3]], different structure")
    for name in ("hamming_7", "steane"):
        c = STD[name]()
        print(f"  {c.name:26} order {_order(c)}")
    r = 3
    H = np.array([[(col >> (r - 1 - b)) & 1 for b in range(r)] for col in range(1, 2 ** r)], np.uint8).T
    sc = css_strings(H, H, "Hamming-CSS[[7,1,3]] self-dual")
    print(f"  {sc.name:26} d={code_distance(H, H)} order {_order(sc)}")
    Hx = np.array([[1, 1, 1, 1, 1, 1, 0, 0, 0], [0, 0, 0, 1, 1, 1, 1, 1, 1]], np.uint8)
    Hz = np.array([[1, 1, 0, 0, 0, 0, 0, 0, 0], [0, 1, 1, 0, 0, 0, 0, 0, 0],
                   [0, 0, 0, 1, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 1, 0, 0, 0],
                   [0, 0, 0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0, 1, 1]], np.uint8)
    shor = css_strings(Hx, Hz, "Shor[[9,1,3]] asymmetric")
    print(f"\nlarger n via the string-only path (analytic order only, no exact check at n=9)")
    print(f"  {shor.name:26} d={code_distance(Hx, Hz)} order {_order(shor)}")


def device(T1=MARRAKESH[0], T2=MARRAKESH[1], gate=MARRAKESH[2]):
    # leak and rounds-to-error at measured device parameters
    K = channel_from_t1t2(T1, T2, gate)
    print(f"T1={T1 * 1e6:.1f}us T2={T2 * 1e6:.1f}us, syndrome cycle {gate * 1e6:.1f}us")
    print(f"{'code':12} {'pop TVD/round':>14} {'rounds->1%':>12}")
    for name in STD:
        leak, d0, d1 = population_leak(STD[name](), K)
        print(f"{name:12} {leak:14.3e} {str(rounds_for_error(d0, d1, 0.01)):>12}")
    lc, _, _ = population_leak(STD["repetition"](), channel_from_t1t2(1e9, T2, gate))
    print(f"control, T1 to infinity: repetition TVD {lc:.2e}")


def held_memory(rounds=300):
    # held, actively corrected memory against the re-preparation regime
    K = channel_from_t1t2(*MARRAKESH)
    print(f"held state with recovery, {rounds} rounds, device parameters")
    for name, o in (("repetition", 1), ("code_4_1_2", 2), ("hamming_7", 3)):
        res = repeated_extraction(STD[name](), kraus_override=K, rounds=rounds, correct=True)
        tot = sum(r["chernoff"] for r in res["rounds"])
        print(f"  {name:12} leak order {o}: partial sum {tot:.4e} nats at {rounds} rounds, "
              f"attack bound {0.5 * math.exp(-tot):.4f}")
    _l, d0, d1 = population_leak(STD["repetition"](), K)
    print(f"  re-preparation, repetition: rounds to 1 percent {rounds_for_error(d0, d1, 0.01)}")
    rp = repeated_extraction(STD["repetition"](), kraus_override=dephasing(0.05), rounds=20, correct=True)
    print(f"  Pauli control, max per-round TVD {max(r['tvd'] for r in rp['rounds']):.2e}")
    print("  the cumulative exponent does not converge on this horizon; these are partial sums")


def worst_pair():
    # is the population axis the most distinguishable logical pair
    grid = state_grid(9, 8)
    print(f"Bloch grid of {len(grid)} logical states, Chernoff maximised over all pairs")
    for ch, param in (("amplitude_damping", 0.2), ("coherent_diagonal", 0.3)):
        print(f"{ch} ({param})")
        for name in ("repetition", "code_4_1_2", "hamming_7"):
            w = worst_case_pair(STD[name](), gamma=param, channel=ch, grid=grid)
            print(f"  {name:12} worst {w['chernoff']:.4f}  axis {w['axis_chernoff']:.4f}  "
                  f"axis is worst: {w['axis_is_worst']}")


def pauli_boundary():
    # syndrome state-dependence for Pauli against non-Pauli channels
    grid = state_grid(7, 6)
    print(f"max pairwise syndrome TVD over {len(grid)} logical states")
    print(f"{'code':12} {'depolarizing':>14} {'dephasing':>12} {'amp damping':>13} {'coherent diag':>15}")
    for name in ("repetition", "code_4_1_2", "hamming_7"):
        c = STD[name]()
        row = []
        for K in (depolarizing(0.1), dephasing(0.1), amplitude_damping(0.2), coherent_diagonal(0.3)):
            ds = [c.syndrome_dist(c.apply(c.logical_state(t, p), K)) for t, p in grid]
            row.append(max(tvd(ds[i], ds[j]) for i in range(len(ds)) for j in range(i + 1, len(ds))))
        print(f"{name:12} {row[0]:14.2e} {row[1]:12.2e} {row[2]:13.3e} {row[3]:15.3e}")


def audit():
    # the attack against its closed form, and the Chernoff grid
    print("one-shot attack against the closed form (1 - TVD)/2, 200000 trials")
    for name, K in (("repetition", amplitude_damping(0.2)), ("code_4_1_2", amplitude_damping(0.2)),
                    ("code_4_1_2 coherent", coherent_diagonal(0.3)), ("hamming_7", amplitude_damping(0.2))):
        c = STD[name.split()[0]]()
        leak, d0, d1 = population_leak(c, K)
        sim = ml_attack(d0, d1, 1, trials=200000, seed=1)
        se = math.sqrt(max(sim * (1 - sim), 1e-12) / 200000)
        print(f"  {name:20} theory {0.5 * (1 - leak):.5f}  simulated {sim:.5f} +/- {se:.5f}")
    c = STD["hamming_7"]()
    _l, d0, d1 = population_leak(c, amplitude_damping(0.2))
    print("Chernoff grid resolution")
    for g in (51, 201, 2001):
        C, s = chernoff_exponent(d0, d1, grid=g)
        print(f"  grid {g:5d}: C={C:.8f} s*={s:.4f}")


def kl_blocks():
    # Knill-Laflamme branch matrices (Leung et al. 1997) beside the syndrome-resolved blocks, amplitude damping
    import numpy as np
    from .analyze import analytic_leak
    from .approx_qec import branch_matrices, branch_spread, fitted_order, population_split, syndrome_blocks
    from .channels import amplitude_damping
    from .codes import STANDARD
    g = 0.1
    M = branch_matrices(STANDARD["code_4_1_2"](), amplitude_damping(g))[(0, 0, 0, 0)]
    ev = sorted(np.linalg.eigvalsh(M))
    ref = sorted([(1 - g) ** 2, 0.5 * (1 + (1 - g) ** 4)])
    print(f"[[4,1,2]] no-jump branch at gamma {g}, eigenvalues of P_C A^dagger A P_C")
    print(f"  this package          {ev[0]:.12f}  {ev[1]:.12f}")
    print(f"  Leung et al. eq. 39   {ref[0]:.12f}  {ref[1]:.12f}")
    print()
    print(f"{'code':12} {'analytic order':>15} {'syndrome slope':>15} {'branch spread slope':>20}")
    fmt = lambda v: "none" if v is None else f"{v:.2f}"
    for name in STANDARD:
        c = STANDARD[name]()
        _leaks, order = analytic_leak(c)
        syn = fitted_order(lambda x: population_split(syndrome_blocks(c, amplitude_damping(x))))
        br = fitted_order(lambda x: branch_spread(c, amplitude_damping(x))[0])
        print(f"{name:12} {str(order if order is not None else 'none'):>15} {fmt(syn):>15} {fmt(br):>20}")


RUNS = {"selftest": selftest, "attack": attack, "leak_order": leak_order, "coherent": coherent,
        "structure": structure, "device": device, "held_memory": held_memory,
        "worst_pair": worst_pair, "pauli_boundary": pauli_boundary, "audit": audit, "kl_blocks": kl_blocks}


def main(argv):
    names = [a for a in argv if not a.startswith("-")] or list(RUNS)
    save = "--save" in argv
    import contextlib
    import io
    import os
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    for n in names:
        if n not in RUNS:
            print(f"unknown run {n}; choose from {', '.join(RUNS)}")
            return 1
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            RUNS[n]()
        text = buf.getvalue()
        print(f"----- {n} -----")
        print(text)
        if save:
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, f"{n}.txt"), "w", encoding="utf-8") as f:
                f.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
