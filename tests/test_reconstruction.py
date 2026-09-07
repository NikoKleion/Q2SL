# tests for the reconstruction package. The numpy parts (device, seed, magic) always run; the torch/ldpc/qiskit
# paths skip when the tool is absent.
import math
import numpy as np

from _harness import needs
import reconstruction as R


# device (numpy)
def test_device_is_css():
    d = R.Device()
    assert int((d.Hz @ d.Hx.T % 2).sum()) == 0


def test_device_simulate_syndrome_matches():
    d = R.Device()
    S, E = d.simulate(200, "x", np.random.default_rng(0))
    assert np.array_equal(S, (E @ d.Hz.T) % 2)


def test_device_fingerprint_has_hot_edges():
    d = R.Device()
    assert len(d.fingerprint()["hot_edges"]) > 0 and d.rz.mean() > d.rx.mean()


# seed collapse (numpy)
def test_account_from_seed_deterministic():
    assert np.array_equal(R.account_from_seed(7, "strong"), R.account_from_seed(7, "strong"))


def test_structured_seed_is_recurrence():
    a = R.account_from_seed(42, "structured")
    for i in range(2, 9):
        assert a[i] == (a[i - 1] + a[i - 2]) % 10


def test_brute_force_matches_analytic():
    for k in (0, 1, 2, 3):
        bf = R.brute_force_residual(14, k, "strong", trials=60)
        an = R.analytic_residual(14, k)
        assert abs(bf - an) < 0.6


# magic (numpy)
def test_magic_sre_of_T_plus():
    from reconstruction.magic import sre_m2, _T, _H
    psi = _T @ (_H @ np.array([1, 0], complex))
    assert abs(sre_m2(psi, 1) - (-math.log2(0.75))) < 1e-3


# torch / ldpc / qiskit paths
def test_pattern_net_predicts():
    needs("torch")
    from reconstruction.pattern_net import Net, predict
    import torch
    net = Net()
    p = predict(net, np.zeros(16, int), np.zeros(16, bool))
    assert p.shape == (16, 10) and np.allclose(p.sum(axis=1), 1.0, atol=1e-4)


def test_device_trained_decoder_runs():
    needs("ldpc")
    from reconstruction import decoder as D
    Se, Ee = D.sim(60, 999)
    g = D.exact_rate_static(np.full(D.N, float(D.DEV.rx.mean())), Se, Ee)
    l = D.exact_rate_static(D.DEV.rx, Se, Ee)
    assert 0.0 <= g <= 1.0 and l >= g - 0.05


def test_device_from_backend():
    needs("qiskit")
    needs("qiskit_ibm_runtime")
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    d = R.device_from_backend(FakeManilaV2(), L=3)
    assert d.n == 2 * 3 * 3 and d.rx.min() > 0 and hasattr(d, "calibrated_from")
