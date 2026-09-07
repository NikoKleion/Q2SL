# Single-qubit noise channel library; each function returns a Kraus list.
import math
import numpy as np

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], complex)
Y = np.array([[0, -1j], [1j, 0]], complex)
Z = np.array([[1, 0], [0, -1]], complex)


def amplitude_damping(gamma):
    # relaxation toward |0>, the non-unital channel that leaks logical population
    return [np.array([[1, 0], [0, math.sqrt(1 - gamma)]], complex),
            np.array([[0, math.sqrt(gamma)], [0, 0]], complex)]


def amplitude_pumping(gamma):
    # mirror of damping, relaxation toward |1>
    return [np.array([[math.sqrt(1 - gamma), 0], [0, 1]], complex),
            np.array([[0, 0], [math.sqrt(gamma), 0]], complex)]


def generalized_amplitude_damping(gamma, p=0.5):
    # finite-temperature amplitude damping; excited-state population 1-p
    a = [np.array([[1, 0], [0, math.sqrt(1 - gamma)]], complex), np.array([[0, math.sqrt(gamma)], [0, 0]], complex)]
    b = [np.array([[math.sqrt(1 - gamma), 0], [0, 1]], complex), np.array([[0, 0], [math.sqrt(gamma), 0]], complex)]
    return [math.sqrt(p) * a[0], math.sqrt(p) * a[1], math.sqrt(1 - p) * b[0], math.sqrt(1 - p) * b[1]]


def channel_from_t1t2(T1, T2, gate_time):
    # build the amplitude-plus-phase-damping Kraus set from T1, T2, and gate time
    g1 = 1.0 - math.exp(-gate_time / T1)
    inv_tphi = max(0.0, 1.0 / T2 - 1.0 / (2.0 * T1))
    lam = 1.0 - math.exp(-2.0 * gate_time * inv_tphi)
    A = [np.array([[1, 0], [0, math.sqrt(1 - g1)]], complex), np.array([[0, math.sqrt(g1)], [0, 0]], complex)]
    P = [np.array([[1, 0], [0, math.sqrt(1 - lam)]], complex), np.array([[0, 0], [0, math.sqrt(lam)]], complex)]
    return [p @ a for p in P for a in A]


def coherent_diagonal(theta):
    # coherent Z-rotation diag(1, e^{i theta}) on every qubit; single-Kraus unitary channel
    return [np.array([[1, 0], [0, np.exp(1j * theta)]], complex)]


def depolarizing(p):
    # Pauli channel; syndrome is state-independent, so leaks nothing
    s = math.sqrt(p / 3.0)
    return [math.sqrt(1 - p) * I2, s * X, s * Y, s * Z]


def dephasing(p):
    # pure Z-dephasing, a unital Pauli channel
    return [math.sqrt(1 - p) * I2, math.sqrt(p) * Z]


LIBRARY = {
    "amplitude_damping": amplitude_damping,
    "generalized_amplitude_damping": generalized_amplitude_damping,
    "coherent_diagonal": coherent_diagonal,
    "depolarizing": depolarizing,
    "dephasing": dephasing,
}
