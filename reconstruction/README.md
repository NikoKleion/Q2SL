# reconstruction

The full reconstruction. It fuses several information sources onto one credit-card posterior:

- a trained pattern net (torch): order-agnostic masked-digit prediction from whatever digits are revealed.
- a device-trained BP+OSD decoder (ldpc): trained on a specific device's noise fingerprint, it beats the
  device-agnostic decoder. The device can be synthetic or calibrated from a real Qiskit
  backend.
- an account-seed factor: if the account RNG is seeded with b bits, the secret is min(29.9, b) bits, and revealed
  digits filter the seed set by about 3.32 bits each.
- a magic trust weight (stabilizer Renyi entropy): a magic-rich carrier tempers the emitter reads.

## Contents

- `device.py` the toric-code device and its noise fingerprint; `device_from_backend` builds one from a Qiskit
  backend's calibration.
- `pattern_net.py` the torch masked-digit predictor.
- `decoder.py` the device-trained versus device-agnostic BP+OSD comparison.
- `seed.py` the account-seed collapse (brute force and analytic).
- `magic.py` stabilizer Renyi entropy.
- `scenario.py` the scenario that fuses all of the above.
- `models/` trained weights for the pattern net and neural decoder.

## Usage

```bash
python -m reconstruction          # the full reconstruction, needs torch and ldpc
python -m reconstruction.decoder  # device-trained versus agnostic decoder
python -m reconstruction.seed     # account-seed collapse
```

The full scenario needs torch and ldpc; `device`, `magic`, and the seed collapse are numpy only. Simulation only.
