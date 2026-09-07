# syndrome_leakage

Measures what the error-correction syndrome reveals about the encoded logical state.

Under a Pauli channel the syndrome distribution is the same for every logical state (Kobori and Todo,
arXiv:2406.08981). Under amplitude damping or a coherent rotation it can depend on the state. For a channel
the code corrects only approximately, the detection probabilities vary across the codespace (Leung,
Nielsen, Chuang and Yamamoto, 1997), and for a diagonal unitary Hu, Liang and Calderbank give them in
closed form. This package computes the size of that dependence, the order at which it appears in the
noise strength, and the error rate of a likelihood-ratio test that reads only the syndrome record.

The analysis is simulation, with device parameters entering as numbers. `hardware.py` additionally builds
circuits to measure the leak on a real backend; the measured data is in `results/`.

## Contents

- `core.py` the `Code` class, stabilizer projectors, and the exact density-matrix engine.
- `analyze.py` leakage measures, the analytic leak order, and the `analyze()` entry point.
- `codes.py` standard codes: repetition, [[4,1,2]], Hamming [[7,1,3]], Steane, five-qubit.
- `css.py` build a code from CSS check matrices over GF(2), with a strings-only path for codes too large
  to construct as density matrices, and a code-distance check.
- `channels.py` single-qubit channels, including `channel_from_t1t2` built from measured T1, T2 and a gate
  time, and `coherent_diagonal` for a coherent Z-rotation.
- `wasserstein.py` a Wasserstein-1 leak distance under the Hamming ground metric.
- `eavesdrop.py` the likelihood-ratio attack, the Chernoff exponent, rounds-to-error, the worst-case
  logical pair search, and repeated syndrome extraction.
- `kl_check.py` the analytic leak order against the codeword amplitude-damping distance.
- `approx_qec.py` Knill-Laflamme branch matrices after Leung, Nielsen, Chuang and Yamamoto (1997), and the
  same matrices resolved by syndrome.
- `hlc.py` syndrome probabilities of a CSS code under a transversal Z-rotation, from the generator
  coefficients of Hu, Liang and Calderbank (arXiv:2109.13481).
- `hardware.py` circuits and analysis for measuring the leak on a real backend, and the bridge that reads a
  backend's T1, T2 and gate durations into the channel and the attack.
- `experiments.py` every documented run, one command each.
- `results/` saved output of those runs, and the measured hardware data.

## Requirements

Python 3.11 or newer and numpy. `wasserstein.py` uses scipy when present and falls back to a lower bound
without it.

## Self-test

```bash
python -m syndrome_leakage.analyze --selftest
```

The analytic leak order must match the measured slope of the exact simulation on every standard code.

## Documentation

- [USAGE.md](USAGE.md) how to run each analysis.
- [RESULTS.md](RESULTS.md) every run, what it measures, its control, and its output.
