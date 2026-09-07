# Tests

Regression tests for the three packages and the suite.

## Run

Full suite (pytest, with scipy and pyzx so nothing skips):

```bash
python -m pytest tests
```

Zero-dependency runner (base python, numpy only; scipy/pyzx/qiskit tests skip):

```bash
python tests/run_tests.py
```

## Coverage

- `test_syndrome_leakage.py` analytic against exact, the CSS backend, Wasserstein, and the T1/T2 channel.
- `test_pauli_boundary.py`, `test_kl_check.py`, `test_eavesdrop.py`, `test_worst_pair.py`,
  `test_coherent_diagonal.py`, `test_scaling.py`, `test_device_grounded.py`, `test_held_memory.py` one file
  per documented run in `syndrome_leakage/RESULTS.md`, pinning its numbers.
- `test_hardware_bridge.py` the device bridge in `syndrome_leakage/hardware.py`, on a stub backend.
- `test_approx_qec.py` the Knill-Laflamme branch matrices against equation 39 of Leung et al., and the
  syndrome blocks against the exact syndrome distributions.
- `test_hlc.py` equation 91 of Hu, Liang and Calderbank against the exact simulation.
- `test_entropy_fusion.py` closed-form scoring versus Monte Carlo, exact checksum convolution, the
  read-channel and reveals regressions, adaptivity, and the observed-read bridge.
- `test_reconstruction.py` the numpy parts always; the torch, ldpc and qiskit parts skip when absent.
- `test_suite.py` all modules run, SARIF validity, severity triage.
- `test_q2sl.py` the command-line dispatch.
