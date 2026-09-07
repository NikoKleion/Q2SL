# entropy_fusion.fisher: expert redundancy as a Fisher-Rao angle between score directions.
import numpy as np


def _fisher_corr(la, lb, p):
    # Fisher-Rao cosine between two score vectors under p; 1 = parallel/redundant, 0 = orthogonal
    p = p / p.sum()
    ma, mb = (p * la).sum(), (p * lb).sum()
    cov = (p * (la - ma) * (lb - mb)).sum()
    va, vb = (p * (la - ma) ** 2).sum(), (p * (lb - mb) ** 2).sum()
    if va <= 1e-15 or vb <= 1e-15:
        return 0.0
    return float(cov / np.sqrt(va * vb))


def _is_instance_independent(expert, payload):
    # true if the expert's likelihood ignores the instance, so one evaluation is exact
    from .experts import HardwareExpert
    if isinstance(expert, HardwareExpert):
        return False
    k = np.zeros(payload.n, bool)
    a = expert.likelihood(payload, np.zeros(payload.n, int), k)
    b = expert.likelihood(payload, (np.arange(payload.n) % payload.A).astype(int), k)
    return np.array_equal(a, b)


def fisher_cosine(payload, expert_a, expert_b, samples=300, seed=0):
    # average Fisher-Rao cosine between two experts' score directions
    if _is_instance_independent(expert_a, payload) and _is_instance_independent(expert_b, payload):
        samples = 1
    cos = []
    for s in range(samples):
        rng = np.random.default_rng(seed * 100003 + s)
        inst = payload.generate(rng); known = np.zeros(payload.n, bool)
        La = expert_a.likelihood(payload, inst, known); Lb = expert_b.likelihood(payload, inst, known)
        for i in range(payload.n):
            la = np.log(np.clip(La[i], 1e-12, None)); lb = np.log(np.clip(Lb[i], 1e-12, None))
            p = La[i] * Lb[i]; ps = p.sum()
            if ps > 0:
                cos.append(_fisher_corr(la, lb, p / ps))
    return float(np.mean(cos)) if cos else 0.0


def redundancy_weight(payload, new_expert, included_experts, samples=200, seed=1):
    # trust weight for adding new_expert: 1 minus its max Fisher-Rao cosine with any included expert
    if not included_experts:
        return 1.0
    m = max(abs(fisher_cosine(payload, new_expert, e, samples, seed)) for e in included_experts)
    return float(np.clip(1.0 - m, 0.0, 1.0))


def main():
    from .registry import SpecPayload
    from .experts import FieldFormatExpert, PatternExpert, HardwareExpert

    def structured_bits(n, c, seed):
        rng = np.random.default_rng(seed); q = 1.0 / (1.0 + np.exp(-c * rng.standard_normal(n)))
        return SpecPayload(f"bits(c={c})", n, 2, lambda r: (r.random(n) < q).astype(int))

    pay = structured_bits(16, 2.5, seed=0)
    pat = PatternExpert(pay)
    hw_good = HardwareExpert(reliability=0.9)
    hw_weak = HardwareExpert(reliability=0.55)
    uni = HardwareExpert(reliability=0.5)

    print("# Fisher-Rao cosine between experts (1 = substitutes/redundant, 0 = complements/independent)")
    print(f"#   pattern  vs  strong hardware (p=0.9) : {fisher_cosine(pay, pat, hw_good):+.3f}   both point at the true value -> substitutes")
    print(f"#   pattern  vs  weak hardware   (p=0.55): {fisher_cosine(pay, pat, hw_weak):+.3f}")
    print(f"#   pattern  vs  uniform read    (p=0.5) : {fisher_cosine(pay, pat, uni):+.3f}   uniform carries no direction -> ~0")
    print(f"#\n#   redundancy weight for adding strong hardware given the pattern is already in: "
          f"{redundancy_weight(pay, hw_good, [pat]):.2f}")
    print("#   high Fisher cosine -> low redundancy weight: the second read is largely")
    print("#   redundant with the classical pattern.")


if __name__ == "__main__":
    main()
