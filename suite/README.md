# suite

One registry that runs the other packages as modules and emits SARIF 2.1.0. Each module declares a dimension (the
source it consumes) and a target (what it finds). You target a thing and the suite runs the modules that apply.

## Contents

- `core.py` the module registry, the Finding type, and the `find()` dispatcher.
- `modules.py` the analysis modules: syndrome leak, syndrome eavesdropper, secret reconstruction, gate identity,
  physical leakage, device reconstruction, entropy trojan.
- `report.py` severity scoring and SARIF 2.1.0 export.
- `zx_fingerprint.py` ZX-calculus gate identity (needs pyzx).

## Usage

```python
import suite
for f in suite.find():
    print(f)
print(suite.report.run_report())   # SARIF 2.1.0
```

Or from the command line:

```bash
python -m suite
python -m suite find gate-identity
```

Simulation only.
