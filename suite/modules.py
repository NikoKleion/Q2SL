# suite.modules: the analysis modules, one per (dimension, target).
import os, sys, math
import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from .core import Module, Finding, register


@register
class LogicalDataLeak(Module):
    name = "logical_data_leak"
    dimension = "syndrome"
    target = "logical-data-leak"
    summary = "what a code's syndrome leaks about the ENCODED LOGICAL data under a noise channel (population/phase)"

    def run(self, code="steane", channel="amplitude_damping", gamma=0.2, **_):
        import syndrome_leakage as sl
        c = sl.codes.STANDARD[code]()
        r = sl.analyze(c, channel, gamma)
        head = (f"population LEAKS at order gamma^{r.analytic_order}" if r.leaks else "population PROTECTED") \
               + f"; phase {'PROTECTED' if r.phase < 1e-9 else 'LEAKS'}"
        return Finding(self.name, self.dimension, self.target, head, f"leak={r.population:.2e}",
                       0.95 if r.validated else 0.6, f"code {c.name}, channel {channel} gamma={gamma}", vulnerable=bool(r.leaks))


@register
class SyndromeEavesdropper(Module):
    name = "syndrome_eavesdropper"
    dimension = "syndrome"
    target = "syndrome-eavesdropper"
    summary = "rounds of syndrome data an adversary needs to identify the encoded logical state, by achieved attack"

    def run(self, code="hamming_7", gamma=0.2, rounds=200, trials=2000, **_):
        import syndrome_leakage as sl
        c = sl.codes.STANDARD[code]()
        res = sl.eavesdrop.attack_point(c, gamma=gamma, rounds=(rounds,), trials=trials)
        row = res["rows"][0]
        need = res["rounds_for_1pct"]
        if need is None:
            head = f"syndrome carries no state dependence: attack stays at chance ({row['attack_error']:.2f})"
        else:
            head = (f"attack error {row['attack_error']:.3f} after {rounds} rounds; "
                    f"{need} rounds reach 1 percent")
        return Finding(self.name, self.dimension, self.target, head,
                       f"eve={row['attack_error']:.3f}",
                       0.9 if need is not None else 0.6,
                       f"code {c.name}, amplitude_damping gamma={gamma}, likelihood-ratio attack; "
                       f"Bhattacharyya bound reports {row['bhattacharyya_bound']:.3f}",
                       vulnerable=need is not None)


@register
class SecretReconstruction(Module):
    name = "secret_reconstruction"
    dimension = "classical+hardware"
    target = "secret-reconstruction"
    summary = "residual guessing entropy of a structured secret, fusing classical patterns and a hardware read"

    def run(self, payload="phone_number", reveals=0, hardware_p=0.85, **_):
        import entropy_fusion as ef
        pay = ef.make_payload(payload)
        experts = [ef.make_expert("field_format"), ef.make_expert("pattern", pay),
                   ef.make_expert("hardware", reliability=hardware_p), ef.make_expert("revealed")]
        bits, acc = ef.evaluate(pay, experts, reveals=reveals)
        blind = pay.blind_bits()
        return Finding(self.name, self.dimension, self.target,
                       f"secret collapses {blind:.0f} -> {bits:.1f} bits ({acc:.0%} guess accuracy)",
                       f"{bits:.1f} bits", 0.9, f"payload {pay.name}, {reveals} revealed, hardware p={hardware_p}", vulnerable=bits < 15)


@register
class GateFingerprint(Module):
    name = "gate_fingerprint"
    dimension = "syndrome"
    target = "gate-identity"
    summary = "infer WHICH logical operation ran from its syndrome noise signature (Shukla-Browne-Nishio style)"

    def run(self, alpha=0.6, shots=120, **_):
        from . import covert_channel as cc
        base = cc.device_rates()
        acc = cc.attack_accuracy(base, alpha=alpha, K=int(shots), obs=np.arange(cc.M),
                                 trials=300, rng=np.random.default_rng(2))
        return Finding(self.name, self.dimension, self.target,
                       f"which-gate identifiable from the syndrome at {acc:.0%} accuracy over {shots} shots",
                       f"{acc:.2f} acc", float(acc),
                       "two operations leaving distinct data-dependent syndrome signatures", vulnerable=acc > 0.6)


@register
class PhysicalLeakage(Module):
    name = "physical_leakage"
    dimension = "physical-leakage"
    target = "leakage-events"
    summary = "detect qubits escaping the computational subspace into |2>+ (physical leakage, gladiator/eraser lane)"

    def run(self, n=12, leaked_frac=0.15, window=8, trials=500, **_):
        # toy detector: threshold each qubit's check-firing rate over a window to flag leakage.
        rng = np.random.default_rng(3)
        base_fire, leaked_fire = 0.08, 0.55
        thr = (base_fire + leaked_fire) / 2
        det = tl = fp = tn = 0
        for _ in range(trials):
            leaked = rng.random(n) < leaked_frac
            rates = np.where(leaked, leaked_fire, base_fire)
            obs = (rng.random((window, n)) < rates).mean(axis=0)
            flag = obs > thr
            det += int((flag & leaked).sum()); tl += int(leaked.sum())
            fp += int((flag & ~leaked).sum()); tn += int((~leaked).sum())
        det_rate, fpr = det / max(tl, 1), fp / max(tn, 1)
        return Finding(self.name, self.dimension, self.target,
                       f"physical leakage detected at {det_rate:.0%} (false-positive rate {fpr:.1%})",
                       f"det {det_rate:.2f}", det_rate, f"n={n} qubits, leaked fraction {leaked_frac}, window {window}", vulnerable=True)


@register
class DeviceReconstruction(Module):
    name = "device_reconstruction"
    dimension = "classical+quantum"
    target = "device-reconstruction"
    summary = "fused reconstruction of a structured secret: trained pattern net + device-trained BP+OSD decoder + account seed + magic trust"

    def run(self, reveals=2, samples=20, **_):
        # runs only when torch and ldpc are present (the full reconstruction), otherwise opts out with None
        try:
            from reconstruction import scenario as S
        except Exception:
            return None
        if not (getattr(S, "_HAVE_TORCH", False) and getattr(S, "_HAVE_LDPC", False)):
            return None
        rng = np.random.default_rng(0)
        p = S.Posture(pattern=True, emitter=True, seed=True, b_seed=16, access=0.7, twirl_known=True, label="all levers")
        accs = []
        for _ in range(samples):
            card = S.gen_card(p.b_seed)
            known = np.zeros(16, bool); known[rng.permutation(16)[:reveals]] = True
            post = S.aggregate(card, known, p.experts(card, known), p.luhn)
            accs.append(S.accuracy(post, card))
        acc = float(np.mean(accs))
        return Finding(self.name, self.dimension, self.target,
                       f"secret reconstructs to {acc:.0%} accuracy at {reveals} revealed digits (pattern + device decoder + seed + magic)",
                       f"{acc:.2f} acc", 0.85,
                       f"toric L={S.DEV.L} device, all levers, {reveals} reveals", vulnerable=acc > 0.6)


@register
class EntropyTrojan(Module):
    name = "entropy_trojan"
    dimension = "rng"
    target = "entropy-trojan"
    summary = "audit a supposedly-uniform RNG bitstream for bias or correlation, a hardware trojan or entropy bias"

    def run(self, bias=0.08, corr=0.10, length=20000, **_):
        # simulate a biased/correlated RNG, then audit its min-entropy against the ideal 1 bit/bit.
        rng = np.random.default_rng(4)
        bits = np.empty(length, int); prev = 0
        for i in range(length):
            p = 0.5 + bias + corr * (prev - 0.5) * 2.0
            b = int(rng.random() < min(max(p, 0.01), 0.99)); bits[i] = b; prev = b
        p1 = float(bits.mean())
        hmin = -math.log2(max(p1, 1 - p1))
        c = float(np.corrcoef(bits[:-1], bits[1:])[0, 1])
        trojan = abs(p1 - 0.5) > 0.02 or abs(c) > 0.03
        return Finding(self.name, self.dimension, self.target,
                       (f"TROJAN: biased/correlated RNG" if trojan else "RNG looks clean")
                       + f" (P(1)={p1:.3f}, lag-1 corr={c:+.3f})",
                       f"H_min={hmin:.3f}/bit", 0.9 if trojan else 0.7,
                       f"min-entropy {hmin:.3f} bits/bit vs ideal 1.0, over {length} bits", vulnerable=bool(trojan))
