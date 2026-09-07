# syndrome leakage on a real backend: repetition-code circuits, the idle-delay sweep analysis, and the
# bridge that reads T1, T2 and gate durations from a Qiskit backend
import math

import numpy as np

from .core import tvd
from .eavesdrop import chernoff_exponent, ml_attack

DATA = (0, 1, 2)
ANCILLA = (3, 4)


def build_circuits(delays_s, qubits=None):
    # for each idle delay, one circuit preparing |0_L> and one preparing |1_L>, then one round of
    # Z-stabilizer extraction (ZZI, IZZ) onto two ancillas
    from qiskit import QuantumCircuit
    data = list(qubits[:3]) if qubits else list(DATA)
    anc = list(qubits[3:5]) if qubits else list(ANCILLA)
    circs, labels = [], []
    for t in delays_s:
        for prep in (0, 1):
            qc = QuantumCircuit(5, 2)
            if prep == 1:
                for i in range(3):
                    qc.x(i)
            qc.barrier()
            if t > 0:
                for i in range(3):
                    qc.delay(t, i, unit="s")
            qc.barrier()
            qc.cx(0, 3); qc.cx(1, 3)          # ZZI
            qc.cx(1, 4); qc.cx(2, 4)          # IZZ
            qc.measure(3, 0); qc.measure(4, 1)
            circs.append(qc)
            labels.append((t, prep))
    return circs, labels


def syndrome_dist_from_counts(counts, shots):
    # two ancilla bits -> a distribution over the four syndromes
    d = np.zeros(4, float)
    for bits, n in counts.items():
        b = bits.replace(" ", "")
        d[int(b, 2)] += n
    return d / max(d.sum(), 1)


def analyse(dists, labels, T1=None):
    # dists keyed by (delay, prep); report the leak against idle delay
    out = []
    for t in sorted({t for t, _ in labels}):
        d0, d1 = dists[(t, 0)], dists[(t, 1)]
        leak = tvd(d0, d1)
        C, _s = chernoff_exponent(d0, d1)
        row = {"delay_s": t, "tvd": leak, "chernoff": C,
               "attack_1shot": ml_attack(d0, d1, 1, trials=200000, seed=1),
               "theory_1shot": 0.5 * (1 - leak)}
        if T1:
            row["gamma"] = 1.0 - math.exp(-t / T1)
        out.append(row)
    return out


def report(rows, T1=None):
    L = ["measured syndrome leakage, 3-qubit repetition code, one round of Z-stabilizer extraction",
         "the amplitude-damping leak grows with idle time; a preparation or readout offset does not",
         ""]
    head = f"  {'delay (us)':>11} {'gamma':>8} {'syndrome TVD':>13} {'Chernoff':>10} {'1-shot attack':>14}"
    L.append(head)
    L.append("  " + "-" * (len(head) - 2))
    for r in rows:
        g = f"{r.get('gamma', float('nan')):8.4f}" if T1 else "       -"
        L.append(f"  {r['delay_s'] * 1e6:11.1f} {g} {r['tvd']:13.4f} {r['chernoff']:10.4f} "
                 f"{r['attack_1shot']:14.4f}")
    L.append("")
    L.append("  a leak that is flat in delay would indicate preparation or readout asymmetry, not damping")
    return "\n".join(L)


# device bridge: T1, T2 and gate durations from a Qiskit backend into the leak analysis
def available():
    try:
        import qiskit  # noqa: F401
        return True
    except Exception:
        return False


def gate_duration(backend, name, qubits, default=None):
    # seconds, from the BackendV2 Target first, then BackendV1 properties
    try:
        inst = backend.target[name][tuple(qubits)]
        if inst is not None and inst.duration is not None:
            return float(inst.duration)
    except Exception:
        pass
    try:
        return float(backend.properties().gate_length(name, list(qubits)))
    except Exception:
        return default


def t1t2_from_backend(backend, qubit):
    try:
        qp = backend.target.qubit_properties[qubit]
        return float(qp.t1), float(qp.t2)
    except Exception:
        p = backend.properties()
        return float(p.t1(qubit)), float(p.t2(qubit))


def damping_gamma(T1, elapsed):
    # amplitude-damping strength over `elapsed` seconds at relaxation time T1
    if T1 <= 0.0:
        return 1.0
    return float(1.0 - math.exp(-float(elapsed) / float(T1)))


def channel_from_backend(backend, qubit, gate_time=None):
    # relaxation channel from this qubit's T1 and T2 over one gate or idle time
    from .channels import channel_from_t1t2
    T1, T2 = t1t2_from_backend(backend, qubit)
    if gate_time is None:
        gate_time = gate_duration(backend, "sx", (qubit,), default=1e-7)
    return channel_from_t1t2(T1, T2, gate_time)


def syndrome_leak_from_backend(backend, code="hamming_7", qubits=None, syndrome_time=None, rounds=(1, 10, 100)):
    # attack point at the damping strength set by the worst T1 among the data qubits over one extraction cycle
    from . import codes, eavesdrop
    qubits = list(range(backend.num_qubits)) if qubits is None else list(qubits)
    c = codes.STANDARD[code]() if isinstance(code, str) else code
    use = qubits[:c.n]
    t1s = []
    for q in use:
        try:
            t1s.append(t1t2_from_backend(backend, q)[0])
        except Exception:
            pass
    if not t1s:
        return None
    T1 = float(min(t1s))
    if syndrome_time is None:
        two_q = None
        for g in ("cx", "ecr", "cz"):
            two_q = gate_duration(backend, g, (use[0], use[1]))
            if two_q is not None:
                break
        syndrome_time = (two_q if two_q is not None else 1e-6) * 4.0
    gamma = damping_gamma(T1, syndrome_time)
    res = eavesdrop.attack_point(c, gamma=gamma, rounds=rounds)
    name = getattr(backend, "name", "backend")
    res["backend"] = name() if callable(name) else name
    res["T1"] = T1
    res["syndrome_time"] = float(syndrome_time)
    res["qubits"] = use
    return res
