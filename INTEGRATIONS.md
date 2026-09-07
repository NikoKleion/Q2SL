# External tools

The external tools q2sl uses and where. Each adapter is optional and activates when the tool is installed.

- Qiskit (with qiskit-ibm-runtime) quantum hardware. `syndrome_leakage/hardware.py` reads a backend's T1, T2
  and gate durations into the relaxation channel and the attack, and builds and analyses the circuits that
  measure the leak on a device. `reconstruction.device_from_backend` builds the decoder's device from a
  backend's calibrated error rates.
- ldpc (BP-OSD) QEC decoding, the decoder in `reconstruction/` (device-trained and device-agnostic).
- torch the trained pattern net and the neural decoder in `reconstruction/`.
- PyZX ZX-calculus circuit equivalence, in `suite/zx_fingerprint.py`.
- scipy the exact Wasserstein leak distance in `syndrome_leakage/wasserstein.py`.

`syndrome_leakage.hardware.available()` reports whether qiskit is present, and the numpy core runs without
any of them.
