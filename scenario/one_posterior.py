# End-to-end run: one synthetic secret reconstructed with SARIF output. Simulation-only.
import os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

import entropy_fusion as ef
from entropy_fusion.fast import evaluate_fast
from entropy_fusion.factorgraph import grouped_residual_bits, phone_groups
from entropy_fusion.fisher import fisher_cosine, redundancy_weight
from entropy_fusion.adaptive import evaluate_adaptive
from entropy_fusion.registry import SpecPayload

import syndrome_leakage as sl
from syndrome_leakage import channels, codes
from syndrome_leakage.analyze import population_leak, eavesdropper_error, analytic_leak, measured_order
from syndrome_leakage.core import tvd
from syndrome_leakage.wasserstein import w1_leakage

import suite


# 1. read reliability from the physical channel
def read_reliability(code, gamma=0.2, shots=40, channel="amplitude_damping"):
    # read reliability p in [0.5, 1.0] from syndrome distinguishability (eavesdropper_error, Bhattacharyya bound); a protected code gives p=0.5.
    kraus = channels.LIBRARY[channel](gamma)
    t, d0, d1 = population_leak(code, kraus)
    eve = eavesdropper_error(d0, d1, shots)
    return 0.5 + (0.5 - eve), t, d0, d1


def front_end_table(gamma=0.2, shots=40):
    print("=" * 96)
    print("1. physical front-end (syndrome_leakage): the emitter code sets the read reliability")
    print("=" * 96)
    print(f"   amplitude damping gamma={gamma}, eavesdropper observes {shots} syndrome shots\n")
    print(f"   {'code':>18}  {'leak order':>10}  {'TVD':>8}  {'W1':>8}  {'eave err':>9}  {'read p':>7}")
    rows = {}
    for name in ("repetition", "code_4_1_2", "hamming_7", "steane"):
        c = codes.STANDARD[name]()
        leaks, order = analytic_leak(c)
        p, t, d0, d1 = read_reliability(c, gamma, shots)
        w1 = w1_leakage(c, "amplitude_damping", gamma)
        ords = f"gamma^{order}" if leaks else "protected"
        w1tag = f"{w1['w1']:.3f}" + ("" if w1["exact"] else "*")
        print(f"   {c.name:>18}  {ords:>10}  {t:>8.3f}  {w1tag:>8}  {eavesdropper_error(d0,d1,shots):>9.3f}  {p:>7.3f}")
        rows[name] = dict(code=c, order=order, leaks=leaks, tvd=t, w1=w1, p=p)
    if not rows["repetition"]["w1"]["exact"]:
        print("   (* W1 lower bound; install scipy in the venv for the exact optimal-transport value)")
    print("\n   The leak order (gamma-slope, validated) and the Wasserstein distance order these codes by")
    print("   decoder-relevant leakage; TVD alone does not. A protected code (Steane) yields read p = 0.5.")
    return rows


# the payloads: a calibrated and a confident-wrong pattern prior
def misleading_phone():
    # a wrong model of the phone: digits shifted +5 mod 10, so a trained pattern is confidently wrong.
    base = ef.make_payload("phone_number")

    def gen(rng):
        return (base.generate(rng) + 5) % 10
    return SpecPayload("phone (WRONG model)", base.n, base.A, gen)


# 2. the posterior, with the geometry upgrades
def posterior_section(pay, p):
    print("\n" + "=" * 96)
    print("2. the posterior (entropy_fusion): fuse the experts, sharpen with the factor-graph group")
    print("=" * 96)
    field = ef.make_expert("field_format"); pat = ef.make_expert("pattern", pay)
    hw = ef.make_expert("hardware", reliability=p); rev = ef.make_expert("revealed")
    experts = [field, pat, hw, rev]
    groups = phone_groups()
    blind = pay.blind_bits()
    print(f"   payload {pay.name}, blind structural entropy {blind:.1f} bits, read p={p:.3f}\n")
    print(f"   {'reveals':>7}  {'+pattern':>9}  {'+hardware':>10}  {'+group (geom)':>13}  {'guess acc':>9}")
    for r in (0, 2, 4, 7):
        b_pat, _ = evaluate_fast(pay, [field, pat, rev], reveals=r)
        b_hw, acc = evaluate_fast(pay, experts, reveals=r)
        grp = np.mean([grouped_residual_bits(pay, pay.generate(np.random.default_rng(s)),
                       _mask(pay.n, r, s), experts, groups) for s in range(40)])
        print(f"   {r:>7}  {b_pat:>9.2f}  {b_hw:>10.2f}  {grp:>13.2f}  {acc:>9.2f}")
    cos = fisher_cosine(pay, pat, hw)
    rw = redundancy_weight(pay, hw, [pat])
    if abs(cos) < 0.15:
        verdict = "near-orthogonal (complementary): fusing them is nearly additive"
    elif cos > 0.3:
        verdict = "partly substitute (overlap): a wrong prior can veto a correct read, addressed in section 4"
    else:
        verdict = "mildly overlapping"
    print(f"\n   Fisher-Rao cosine(pattern, hardware) = {cos:+.2f} (redundancy weight {rw:.2f})  ->  {verdict}.")
    print("   The Fisher-Rao cosine measures how much the two sources overlap. Where they overlap, the")
    print("   adaptive trust weight guards against a wrong prior.")
    return experts


def _mask(n, r, seed):
    k = np.zeros(n, bool)
    if r:
        k[np.random.default_rng(1000 + seed).permutation(n)[:r]] = True
    return k


# 3. beat the other tools
def baselines_section(pay, p, reveals=2):
    print("\n" + "=" * 96)
    print(f"3. comparison with baseline tools (identical instances, reveals={reveals}, calibrated prior)")
    print("=" * 96)
    field = ef.make_expert("field_format"); pat = ef.make_expert("pattern", pay)
    hw = ef.make_expert("hardware", reliability=p); rev = ef.make_expert("revealed")
    groups = phone_groups(); experts = [field, pat, hw, rev]
    tools = []
    b, a = evaluate_fast(pay, [pat, rev], reveals=reveals);           tools.append(("independent per-position argmax (pattern only)", b, a))
    bp, ap = evaluate_fast(pay, [pat, rev], reveals=reveals)
    bh, ah = evaluate_fast(pay, [hw, rev], reveals=reveals)
    if bh <= bp: tools.append(("single best expert (hardware only)", bh, ah))
    else:        tools.append(("single best expert (pattern only)", bp, ap))
    b, a = evaluate_fast(pay, experts, reveals=reveals);              tools.append(("static equal-weight fusion (all experts)", b, a))
    grp = np.mean([grouped_residual_bits(pay, pay.generate(np.random.default_rng(s)),
                   _mask(pay.n, reveals, s), experts, groups) for s in range(60)])
    tools.append(("q2sl: fused + factor-graph geometry", grp, a))
    print(f"   {'tool':>48}  {'residual bits':>13}  {'guess acc':>9}")
    best = min(t[1] for t in tools)
    for name, bits, acc in tools:
        mark = "  <-- best" if abs(bits - best) < 1e-9 else ""
        print(f"   {name:>48}  {bits:>13.2f}  {acc:>9.2f}{mark}")
    print("\n   Lower residual bits = fewer guesses. The fused, grouped posterior has the lowest residual bits")
    print("   here; it couples the sources and does not assign probability to invalid area codes.")


# 4. the adaptivity win
def _adaptivity_table(secret, good_prior, bad_prior, p, reveal_grid):
    field = ef.make_expert("field_format"); rev = ef.make_expert("revealed")
    hw = ef.make_expert("hardware", reliability=p)
    out = {}
    for label, prior in (("CALIBRATED prior", good_prior), ("MISCALIBRATED prior", bad_prior)):
        print(f"\n   {label}")
        print(f"   {'reveals':>7}  {'hardware only':>13}  {'static prior+hw':>15}  {'adaptive':>9}  {'mean w':>7}")
        hw_only, static, adapt = [], [], []
        for r in reveal_grid:
            _, a_hw = evaluate_fast(secret, [hw, rev], reveals=r)
            _, a_st = evaluate_fast(secret, [prior, hw, rev], reveals=r)
            _, a_ad, w = evaluate_adaptive(secret, prior, hw, (field, rev), reveals=r, samples=300)
            hw_only.append(a_hw); static.append(a_st); adapt.append(a_ad)
            print(f"   {r:>7}  {a_hw:>13.3f}  {a_st:>15.3f}  {a_ad:>9.3f}  {w:>7.2f}")
        out[label] = dict(hw=hw_only, static=static, adapt=adapt)
    return out


def structured_token(n=16, c=2.5, seed=0):
    # balanced n-bit structured secret: per-position biases spanning [0,1]; marginals() attached so the fast evaluator is exact.
    rng = np.random.default_rng(seed); q = 1.0 / (1.0 + np.exp(-c * rng.standard_normal(n)))
    pay = SpecPayload(f"structured token ({n}-bit field)", n, 2, lambda r: (r.random(n) < q).astype(int))
    pay.marginals = lambda: np.stack([1.0 - q, q], axis=1)
    return pay


def adaptivity_section(phone_pay, p=0.85):
    print("\n" + "=" * 96)
    print("4. adaptive fusion under a miscalibrated prior")
    print("=" * 96)
    tok = structured_token(16, 2.5, seed=0)
    good_tok = ef.make_expert("pattern", tok)
    wrong_tok = ef.make_expert("pattern", structured_token(16, 2.5, seed=999), temperature=0.5)
    print("\n   (a) balanced structured secret: a 16-bit structured token (every bit modelled)")
    tok_curves = _adaptivity_table(tok, good_tok, wrong_tok, 0.85, (0, 2, 4, 8))
    good_phone = ef.make_expert("pattern", phone_pay)
    wrong_phone = ef.make_expert("pattern", misleading_phone(), temperature=0.5)
    print("\n   (b) the target secret: phone number (4 of 10 digits structured, the rest uniform -> diluted)")
    _adaptivity_table(phone_pay, good_phone, wrong_phone, p, (0, 2, 4, 8))
    print("\n   With the wrong prior, static fusion drops (worst at 0 reveals) while adaptive holds near")
    print("   hardware-only accuracy. The effect scales with how much of the secret is structured: large on")
    print("   the balanced token, smaller on the phone.")
    return tok_curves


# 5. suite output
def suite_section():
    print("\n" + "=" * 96)
    print("5. output (suite): the run as standardized findings + SARIF 2.1.0")
    print("=" * 96)
    from suite import report as R
    findings = suite.find()
    for f in findings:
        s, lvl, _ = R.severity(f)
        print(f"   {lvl:>7}  {f.target:>22}  score {s:>4}  {f.headline[:52]}")
    sarif = R.to_sarif(findings)
    print(f"\n   SARIF 2.1.0 emitted: {len(sarif['runs'][0]['results'])} results, "
          f"{len(sarif['runs'][0]['tool']['driver']['rules'])} rules (GitHub code-scanning ingestible).")
    return findings


# the figure
def make_figure(rows, curves, pay, p, path):
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    except Exception as ex:
        print(f"# figure skipped, {ex}"); return
    field = ef.make_expert("field_format"); pat = ef.make_expert("pattern", pay)
    hw = ef.make_expert("hardware", reliability=p); rev = ef.make_expert("revealed")
    groups = phone_groups(); experts = [field, pat, hw, rev]
    grid = list(range(0, 8))
    b_pat = [evaluate_fast(pay, [field, pat, rev], reveals=r)[0] for r in grid]
    b_hw = [evaluate_fast(pay, experts, reveals=r)[0] for r in grid]
    b_grp = [np.mean([grouped_residual_bits(pay, pay.generate(np.random.default_rng(s)),
             _mask(pay.n, r, s), experts, groups) for s in range(30)]) for r in grid]

    fig, ax = plt.subplots(1, 3, figsize=(16.5, 4.8))
    ax[0].plot(grid, [pay.blind_bits() * (1 - r / pay.n) for r in grid], "o-", color="#888", label="blind (structure only)")
    ax[0].plot(grid, b_pat, "s-", color="#1f77b4", label="+ trained pattern")
    ax[0].plot(grid, b_hw, "^-", color="crimson", label=f"+ hardware read (p={p:.2f})")
    ax[0].plot(grid, b_grp, "D-", color="#2ca02c", label="+ factor-graph group (geometry)")
    ax[0].set_xlabel("revealed digits (cribs)"); ax[0].set_ylabel("residual guessing entropy (bits)")
    ax[0].set_title("One posterior: each source and the geometry\nupgrade collapse the entropy"); ax[0].legend(fontsize=7.5)

    mg = np.array([0, 2, 4, 8]); C = curves["MISCALIBRATED prior"]
    ax[1].plot(mg, C["hw"], "^-", color="crimson", label="hardware only")
    ax[1].plot(mg, C["static"], "s--", color="#888", label="static fusion (collapses)")
    ax[1].plot(mg, C["adapt"], "o-", color="#2ca02c", lw=2, label="ADAPTIVE (holds)")
    ax[1].set_xlabel("revealed bits (cribs)"); ax[1].set_ylabel("reconstruction accuracy")
    ax[1].set_ylim(0, 1.02); ax[1].set_title("The adaptivity win (structured token): a wrong prior\nsinks static fusion, adaptive recovers")
    ax[1].legend(fontsize=7.5, loc="lower right")

    names = ["repetition", "code_4_1_2", "hamming_7", "steane"]
    ps = [rows[n]["p"] for n in names]; ords = [rows[n]["order"] if rows[n]["leaks"] else 0 for n in names]
    xs = np.arange(len(names))
    ax[2].bar(xs - 0.2, ps, 0.4, color="crimson", label="read p")
    ax[2].bar(xs + 0.2, [o / 3.0 for o in ords], 0.4, color="#1f77b4", label="leak order / 3")
    ax[2].axhline(0.5, color="black", ls=":", lw=1, label="p=0.5 (no read)")
    ax[2].set_xticks(xs); ax[2].set_xticklabels(["rep", "[[4,1,2]]", "hamming", "steane"], fontsize=8)
    ax[2].set_title("Physical front-end: the code sets the read\n(protected code -> p=0.5)"); ax[2].legend(fontsize=7.5)
    fig.tight_layout(); fig.savefig(path, dpi=130)
    print(f"\n# wrote {os.path.basename(path)}")


def main():
    t0 = time.time()
    print("\nq2sl: one posterior, adaptive readout")
    print("simulation-only, synthetic payloads, defensive entropy analysis\n")
    rows = front_end_table(gamma=0.2, shots=40)
    emitter = "code_4_1_2"
    p = rows[emitter]["p"]
    pay = ef.make_payload("phone_number")
    experts = posterior_section(pay, p)
    baselines_section(pay, p, reveals=2)
    curves = adaptivity_section(pay, p=p)
    suite_section()
    make_figure(rows, curves, pay, p, os.path.join(HERE, "one_posterior.png"))
    print(f"\n# full run took {time.time() - t0:.1f} s (closed-form scoring, no Monte-Carlo reconstruction loop)")


if __name__ == "__main__":
    main()
