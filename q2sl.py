# q2sl: one entry point for the demos, the suite, and target assessment.
#   python -m q2sl <command> [args]     (or the installed `q2sl <command>`)
import runpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CODES = ("repetition", "five_qubit", "steane", "code_4_1_2", "hamming_7")

COMMANDS = {
    "assess":      "point at a target and run the relevant analyses (a code name, or backend:<name>)",
    "leak":        "syndrome leak self-test (syndrome_leakage)",
    "fusion":      "reconstruction-hardness demo (entropy_fusion)",
    "eavesdrop":   "the syndrome eavesdropper experiment: what an adversary reading only syndromes achieves",
    "reconstruct": "the full reconstruction (needs torch, ldpc)",
    "example":     "the one-posterior end-to-end run",
    "suite":       "run every suite module and print a SARIF summary",
    "all":         "run the fast numpy demos and the suite",
}


# assess: dispatch by target type
def _assess(args):
    pos = [a for a in (args or []) if not a.startswith("--")]
    target = pos[0] if pos else None
    if target is None or target in ("-h", "--help"):
        print("q2sl assess <target> [code]\n")
        print("  a code name:      " + ", ".join(CODES))
        print("  a qiskit backend: backend:<name> [code]  (e.g. backend:manila steane; the leak at the")
        print("                    backend's T1 over one syndrome-extraction cycle, default code hamming_7)")
        return
    if target in CODES:
        return _assess_code(target)
    if target.startswith("backend:"):
        return _assess_backend(target[len("backend:"):], pos[1] if len(pos) > 1 else "hamming_7")
    print(f"unknown target {target!r}; run 'q2sl assess' for the options")


def _assess_code(name, gamma=0.2, shots=40):
    import syndrome_leakage as sl
    from syndrome_leakage.analyze import population_leak, eavesdropper_error
    from syndrome_leakage import channels
    c = sl.codes.STANDARD[name]()
    r = sl.analyze(c, "amplitude_damping", gamma)
    w1 = sl.wasserstein.w1_leakage(c, "amplitude_damping", gamma)
    _, d0, d1 = population_leak(c, channels.LIBRARY["amplitude_damping"](gamma))
    eve = eavesdropper_error(d0, d1, shots)
    order = f"leaks at order gamma^{r.analytic_order}" if r.leaks else "protected"
    w1s = f"{w1['w1']:.3e}" + ("" if w1["exact"] else " (lower bound)")
    print(f"code: {c.name} under amplitude damping gamma={gamma}")
    print(f"  population {order}; phase {'protected' if r.phase < 1e-9 else 'leaks'}")
    print(f"  TVD {r.population:.3e} | W1 {w1s} | eavesdropper error over {shots} shots {eve:.3f}")
    print(f"  read reliability from distinguishability: {0.5 + (0.5 - eve):.3f}")


def _assess_backend(name, code="hamming_7"):
    from syndrome_leakage import hardware
    if not hardware.available():
        print("qiskit not installed (pip install qiskit qiskit-ibm-runtime)")
        return
    if code not in CODES:
        print(f"unknown code {code!r}; one of " + ", ".join(CODES))
        return
    backend = _load_backend(name)
    if backend is None:
        print(f"backend {name!r} not found")
        return
    r = hardware.syndrome_leak_from_backend(backend, code=code)
    if r is None:
        print(f"backend {name!r} reports no T1")
        return
    print(f"backend: {r['backend']}  code: {r['code']}  qubits {r['qubits']}")
    print(f"  T1 {r['T1'] * 1e6:.1f} us, syndrome time {r['syndrome_time'] * 1e6:.3f} us, "
          f"gamma {r['gamma']:.3e}, syndrome TVD per shot {r['tvd']:.3e}")
    print(f"  Chernoff exponent {r['chernoff']:.3e} nats/shot, rounds to 1% error {r['rounds_for_1pct']}")
    for row in r["rows"]:
        print(f"  rounds {row['rounds']:>5}  attack error {row['attack_error']:.4f}  "
              f"Chernoff {row['chernoff_error']:.4f}  Bhattacharyya bound {row['bhattacharyya_bound']:.4f}")


def _load_backend(name):
    try:
        import qiskit_ibm_runtime.fake_provider as m
    except Exception:
        return None
    for cand in (name, "Fake" + name.capitalize() + "V2", "Fake" + name + "V2"):
        cls = getattr(m, cand, None)
        if cls is not None:
            try:
                return cls()
            except Exception:
                pass
    return None


# demos and suite
def _leak(args=None):
    import syndrome_leakage as sl
    sl.selftest()


def _fusion(args=None):
    runpy.run_module("entropy_fusion", run_name="__main__")


def _eavesdrop(args=None):
    from syndrome_leakage import eavesdrop
    eavesdrop.main()


def _reconstruct(args=None):
    from reconstruction import scenario
    scenario.main()


def _showcase(args=None):
    runpy.run_path(os.path.join(HERE, "scenario", "one_posterior.py"), run_name="__main__")


def _suite(args=None):
    import suite
    from suite import report as R
    findings = suite.find()
    for f in findings:
        s, level, _ = R.severity(f)
        print(f"  {level:>7}  {f.target:>28}  {s:>4}  {f.headline[:52]}")
    sarif = R.to_sarif(findings)
    print(f"\n  SARIF 2.1.0: {len(sarif['runs'][0]['results'])} results")


def _all(args=None):
    for name, fn in (("leak", _leak), ("fusion", _fusion), ("suite", _suite)):
        print(f"\n===== {name} =====")
        fn()


DISPATCH = {"assess": _assess, "leak": _leak, "fusion": _fusion, "eavesdrop": _eavesdrop,
            "reconstruct": _reconstruct, "example": _showcase, "suite": _suite, "all": _all}


def main(argv=None):
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print("q2sl <command> [args]\n")
        for c, d in COMMANDS.items():
            print(f"  {c:>12}  {d}")
        return
    fn = DISPATCH.get(argv[0])
    if fn is None:
        print(f"unknown command {argv[0]!r}; run 'q2sl help'")
        return
    fn(argv[1:])


if __name__ == "__main__":
    main()
