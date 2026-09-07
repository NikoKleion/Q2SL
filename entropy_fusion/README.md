# entropy_fusion

Fuse structural experts over a synthetic secret and report the residual min-entropy in bits: how many guesses the
secret still takes given what the experts know. Swap the payload, keep the engine.

## Contents

- `core.py` the Payload and Expert base classes, fusion, scoring, evaluation, and Shapley attribution.
- `experts.py` field format, learned pattern, hardware read, observed read (real measurement outcomes), and
  revealed cribs.
- `payloads.py` credit card (with a Luhn checksum factor), Florida phone number, device error string.
- `fast.py` closed-form evaluate and shapley (exact, no Monte Carlo) for checksum-free payloads.
- `adaptive.py` a fusion policy that tempers a classical prior by an estimated trust weight, so a confident-wrong
  prior does not veto a correct read.
- `fisher.py` the Fisher-Rao redundancy angle between two experts.
- `factorgraph.py` group factors for correlated positions (for example a phone area code).

## Usage

```python
import entropy_fusion as ef
pay = ef.make_payload("phone_number")
experts = [ef.make_expert("field_format"), ef.make_expert("pattern", pay), ef.make_expert("revealed")]
print(ef.evaluate(pay, experts, reveals=2))
```

Defensive, synthetic payloads only.
