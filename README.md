# QEC Syndrome Stabilizer Leakage

`q2sl` measures what a stabilizer code's error-correction syndrome reveals about the encoded logical state.

The analysis runs in simulation on synthetic data, with device parameters entering as numbers. One
measurement on IBM hardware is included; see [RESULTS.md](syndrome_leakage/RESULTS.md).

## Features

- **Syndrome leakage.** The distance between syndrome distributions conditioned on the logical state, the
  order at which the leak appears in the noise strength, and the error rate of an adversary reading only the
  syndrome record. Exact density-matrix and analytic modes, a channel built from measured T1 and T2, and CSS
  construction from check matrices.
- **Knill-Laflamme matrices.** The branch matrices of Leung, Nielsen, Chuang and Yamamoto (1997) and the
  same matrices resolved by syndrome. For a CSS code under a transversal Z-rotation, the syndrome
  probabilities from the generator coefficients of Hu, Liang and Calderbank.
- **Device bridge.** T1, T2 and gate durations read from a Qiskit backend set the channel and the attack
  point. The same module holds the circuits and analysis that measure the leak on a device.
- **Reconstruction.** A BP+OSD decoder, a trained pattern net, and a fusion layer over a structured secret.
  Needs torch and ldpc.
- **Suite.** Runs the analyses as modules and emits SARIF 2.1.0.

## Layout

- `syndrome_leakage/` the leakage tool. See its [USAGE.md](syndrome_leakage/USAGE.md) for how to run it and
  what its limits are, and [RESULTS.md](syndrome_leakage/RESULTS.md) for every documented run.
- `entropy_fusion/` residual guessing entropy when several sources are fused.
- `reconstruction/` the full reconstruction over a structured secret.
- `suite/` one registry that runs the above and emits SARIF.
- `scenario/one_posterior.py` an end-to-end run across the packages.
- `tests/` 85 tests in 16 files, run in CI.
- `INTEGRATIONS.md` the external tools and where they are used.

## Requirements

Python 3.11+ and numpy. Optional: scipy (exact Wasserstein), qiskit (device parameters and the hardware
measurement), pyzx (ZX), torch and ldpc (reconstruction). The core runs without any of them and the
optional paths degrade cleanly.

## Install

```bash
pip install -e .           # core, numpy only
pip install -e ".[full]"   # all extras
```

## Usage

```bash
python -m q2sl                               # list commands
python -m q2sl assess steane                 # a code: syndrome leak analysis
python -m q2sl assess backend:manila steane  # a qiskit backend: the leak at its T1
python -m q2sl eavesdrop                     # the syndrome eavesdropper attack
python -m q2sl suite                         # every suite module, with a SARIF summary
```

The documented runs:

```bash
python -m syndrome_leakage.experiments           # every run
python -m syndrome_leakage.experiments attack    # one run; --save writes syndrome_leakage/results/
```

Individual demos:

```bash
python -m syndrome_leakage
python -m suite
python -m reconstruction        # needs torch and ldpc
```

Tests:

```bash
python -m pytest tests
python tests/run_tests.py       # zero-dependency runner
```

## Assumptions

Synthetic data throughout, apart from the hardware measurement in `syndrome_leakage/results/`. No real
records.

## Related

Entropy assessment and device attestation for quantum random number generators:
[qrng-attest](https://github.com/NikoKleion/qrng-attest), Apache 2.0.

## References

- Gottesman, Stabilizer codes and quantum error correction, arXiv:quant-ph/9705052.
- Knill and Laflamme, Phys. Rev. A 55, 900 (1997): the error-correction conditions.
- Leung, Nielsen, Chuang and Yamamoto, Phys. Rev. A 56, 2567 (1997), arXiv:quant-ph/9704002: approximate
  error-correction conditions and the [[4,1,2]] code under amplitude damping.
- Nielsen and Chuang, Quantum Computation and Quantum Information, section 8.3: amplitude damping and
  relaxation channels.
- Kretschmann, Kribs and Spekkens, arXiv:0711.3438: private and correctable subsystems.
- Cover and Thomas, Elements of Information Theory, section 11.9: the Chernoff information.
- Neyman and Pearson, Phil. Trans. R. Soc. A 231, 289 (1933): the likelihood-ratio test.
- Kobori and Todo, arXiv:2406.08981: the syndrome distribution under a Pauli channel is the same for
  every logical state.
- Hu, Liang and Calderbank, arXiv:2109.13481: syndrome probabilities under a diagonal unitary, and the
  condition for them to be independent of the encoded state.
- Shukla, Browne and Nishio, arXiv:2607.12174: syndrome data as a decoder side channel.

## Version

v1.2. `approx_qec.py` computes the Knill-Laflamme branch matrices of Leung, Nielsen, Chuang and Yamamoto,
and the same matrices resolved by syndrome, with the `kl_blocks` run. `hlc.py` computes the syndrome
probabilities of a CSS code under a transversal Z-rotation from the generator coefficients of Hu, Liang
and Calderbank. Tests check both against the exact engine.

## License

PolyForm Noncommercial License 1.0.0, see [LICENSE.md](LICENSE.md). Noncommercial use, study and
modification are permitted; commercial use requires a separate license. Copyright 2026 Nikolas Klein.
