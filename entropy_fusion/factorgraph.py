# entropy_fusion.factorgraph: score correlated positions as joint group factors.
import math
import numpy as np

from .core import fuse
from .payloads import FL_AREA


def phone_groups():
    # phone factor structure: one group factor over the area code (positions 0,1,2), singletons for the rest
    area = [tuple(int(d) for d in a) for a in FL_AREA]
    return [([0, 1, 2], area)] + [([i], None) for i in range(3, 10)]


def _perpos_like(payload, instance, known, experts):
    # product of the experts' per-position likelihoods (unary factors)
    L = np.ones((payload.n, payload.A))
    for e in experts:
        L = L * e.likelihood(payload, instance, known)
    return L


def grouped_residual_bits(payload, instance, known, experts, groups):
    # residual bits summing each group's joint min-entropy over its valid tuples
    L = _perpos_like(payload, instance, known, experts)
    total = 0.0
    for positions, valid in groups:
        if valid is None:
            p = L[positions[0]]; p = p / max(p.sum(), 1e-300)
            total += -math.log2(max(p.max(), 1e-12))
            continue
        w = []
        for t in valid:
            wt = 1.0
            for pos, val in zip(positions, t):
                if known[pos] and int(instance[pos]) != val:
                    wt = 0.0; break
                wt *= L[pos, val]
            w.append(wt)
        w = np.array(w); s = w.sum()
        if s <= 0:
            total += math.log2(len(valid) or 1); continue
        w = w / s
        total += -math.log2(max(w.max(), 1e-12))
    return total


def independent_residual_bits(payload, instance, known, experts):
    # base scoring: every position independent
    from .core import residual_bits
    return residual_bits(fuse(payload, instance, known, experts))


def evaluate_both(payload, experts, groups, reveals=0, samples=400, seed=0):
    ind, grp = [], []
    for s in range(samples):
        rng = np.random.default_rng(seed * 100003 + s)
        inst = payload.generate(rng)
        known = np.zeros(payload.n, bool)
        if reveals:
            known[rng.permutation(payload.n)[:reveals]] = True
        ind.append(independent_residual_bits(payload, inst, known, experts))
        grp.append(grouped_residual_bits(payload, inst, known, experts, groups))
    return float(np.mean(ind)), float(np.mean(grp))


def main():
    from .payloads import PhoneNumber
    from .experts import FieldFormatExpert, PatternExpert, RevealExpert
    pay = PhoneNumber()
    experts = [FieldFormatExpert(), PatternExpert(pay), RevealExpert()]
    groups = phone_groups()
    print("# factor-graph scoring: a correlated group (the area code) as one joint factor vs per-position marginals")
    print(f"# the area code is 1 of {len(FL_AREA)} valid triples = {math.log2(len(FL_AREA)):.1f} bits jointly,")
    print(f"# but per-position field allows the full digit product, over-counting it.\n")
    print(f"#   {'reveals':>7}  {'independent (base)':>18}  {'factor-graph (grouped)':>22}  {'bits recovered':>14}")
    for r in (0, 2, 4, 7):
        ind, grp = evaluate_both(pay, experts, groups, reveals=r)
        print(f"#   {r:>7}  {ind:>18.2f}  {grp:>22.2f}  {ind - grp:>14.2f}")
    print("\n# the grouped (factor-graph) residual is lower because it never spends entropy on invalid area codes.")
    print("# the general form: represent the payload as a factor graph, let experts define unary, group,")
    print("# and checksum factors, and run belief propagation. The base fuse() is the all-unary special case.")


if __name__ == "__main__":
    main()
