# Results

Output in `results/`, regenerated with:

```bash
python -m syndrome_leakage.experiments --save
```

All simulation is exact and deterministic except the attack simulation, which samples syndrome records with
a fixed seed. Where a simulated run uses device parameters they are the medians of IBM `ibm_marrakesh`,
T1 163.3 us and T2 77.0 us, with a 1 us syndrome-extraction cycle.

The final section, `hardware`, is measured on IBM `ibm_fez`. It is not part of
`experiments.py`, since it needs a provider account and queue time; its data is saved under `results/`.

---

## Setup

### Synthetic

Exact density-matrix simulation. One single-qubit Kraus channel is applied independently to every physical
qubit of the code. Syndrome probabilities are `Tr(P_s rho)` with the stabilizer projectors constructed in
full, so the stabilizer measurement is ideal: no ancillas, no gate error, no measurement error. Logical
states come from `code.logical_state(theta, phi)`. Every quantity is deterministic; the only sampling in
the package is the attack simulation, which draws syndrome records and carries a fixed seed.

This is the setting for `selftest`, `attack`, `leak_order`, `coherent`, `structure`, `device`,
`held_memory`, `worst_pair`, `pauli_boundary`, `audit` and `kl_blocks`. The `device` run differs from the
others only in taking its channel from measured T1 and T2, where the others use a free parameter.

### Hardware

IBM `ibm_fez`, 4000 shots per circuit. A 3-qubit repetition code on five qubits: three data qubits and two
ancillas. Each circuit prepares the logical state, idles for a fixed delay, extracts both Z-stabilizers,
and measures the two ancillas.

| step | operation |
|---|---|
| prepare | identity for \|0_L>, X on all three data qubits for \|1_L> |
| idle | `delay(t)` on the data qubits, t in {0, 20, 50, 100} us |
| extract ZZI | CX(d0, a0), CX(d1, a0) |
| extract IZZ | CX(d1, a1), CX(d2, a1) |
| measure | both ancillas, giving one of four syndromes |

Transpiled at optimization level 1 with `scheduling_method="alap"` and `seed_transpiler=7`; scheduling is
required because the circuits carry explicit delays. Layout and routing were left to the transpiler.

The hardware setting adds gate error on the four CX gates, readout error on the ancillas, and a
transpiler-chosen layout, all of which are absent from the synthetic setting. The delay sweep varies the
amplitude-damping contribution with idle time and leaves the additions above fixed.

---

## selftest

The analytic leak order is derived from the stabilizer weight structure; the exact density-matrix
simulation is the ground truth. This checks one against the other on every standard code.

Control: the phase leak must stay below 1e-9, and codes that protect the logical population must report no
leak.

| code | verdict | analytic order | measured slope |
|---|---|---|---|
| repetition | leaks | 1 | 0.96 |
| [[4,1,2]] | leaks | 2 | 1.93 |
| Hamming [[7,1,3]] | leaks | 3 | 2.90 |
| Steane [[7,1,3]] | protected | - | - |
| five-qubit [[5,1,3]] | protected | - | - |

The measured slope of the leak against noise strength matches the analytic order on every leaking code.

---

## pauli_boundary

The maximum pairwise syndrome TVD over 32 logical states spanning the Bloch sphere. Zero means the syndrome
distribution is the same whichever state is encoded. Kobori and Todo (arXiv:2406.08981) state this for
Pauli noise.

| code | depolarizing | dephasing | amplitude damping | coherent diagonal |
|---|---|---|---|---|
| repetition | 9.7e-17 | 0 | 4.80e-01 | 0 |
| [[4,1,2]] | 1.3e-16 | 8.3e-17 | 1.02e-01 | 3.19e-01 |
| Hamming [[7,1,3]] | 3.9e-16 | 2.6e-16 | 1.74e-02 | 7.63e-03 |

Pauli channels give machine-precision zero across the whole sphere. Non-Pauli channels do not.

Steane and the five-qubit code also give machine-precision zero under amplitude damping. Over the same
32 states their maximum pairwise syndrome TVD stays
at or below 2.0e-16 at gamma 0.1, 0.3, 0.5, 0.7, 0.9 and 0.99. The test
`test_protected_codes_hold_at_every_noise_strength` pins this.

---

## leak_order

The analytic leak order beside the amplitude-damping population distance, the minimum weight w for which
some weight-w number operator has a different expectation on the two codewords. The second quantity comes
from the codewords alone and is independent of the stabilizer-group algebra the first uses.

For the [[4,1,2]] code, Leung, Nielsen, Chuang and Yamamoto (1997) find the detection probabilities vary
across the codespace at order gamma^2. The analytic order for that code is 2.

| code | analytic order | AD population distance | equal |
|---|---|---|---|
| repetition | 1 | 1 | yes |
| [[4,1,2]] | 2 | 2 | yes |
| Hamming [[7,1,3]] | 3 | 3 | yes |
| Steane [[7,1,3]] | none | 3 | no |
| five-qubit [[5,1,3]] | none | 5 | no |

The two quantities agree on the three leaking codes and diverge on Steane and the five-qubit code, whose
codewords separate at finite weight while the syndrome distribution does not change. The analytic order is
therefore not the codeword distance.

---

## attack

The error rate of a likelihood-ratio test on the syndrome record, beside the Chernoff rate and the
Bhattacharyya bound. The likelihood-ratio test is the most powerful test for independent shots (Neyman
and Pearson, 1933).
Hamming [[7,1,3]] under amplitude damping at gamma 0.2, syndrome TVD 1.741e-02, Chernoff exponent
0.001002 nats at s* = 0.485, 200000 trials per point.

Control: the one-shot closed form. For a single shot at equal priors the minimum error is exactly
(1 - TVD)/2 = 0.4913, and the simulation returns 0.4908 +/- 0.0011.

| rounds | attack error (200k trials, 1 SE) | Chernoff rate | Bhattacharyya bound |
|---|---|---|---|
| 1 | 0.4908 +/- 0.0011 | 0.4995 | 0.4995 |
| 10 | 0.4518 +/- 0.0011 | 0.4950 | 0.4950 |
| 50 | 0.3782 +/- 0.0011 | 0.4756 | 0.4756 |
| 200 | 0.2625 +/- 0.0010 | 0.4092 | 0.4093 |

At 200 rounds the bound gives 0.409 and the attack reaches 0.2625. Rounds of syndrome data to reach 1
percent error:

| code | gamma 0.1 | gamma 0.2 | gamma 0.3 |
|---|---|---|---|
| repetition | 15 | 8 | 5 |
| [[4,1,2]] | 296 | 91 | 52 |
| Hamming [[7,1,3]] | 26510 | 4595 | 1991 |

Steane and the five-qubit code reach no round count.

Precision: the standard error of the simulated attack is sqrt(e(1-e)/trials). At 200000 trials it is about
0.001, so three decimals are reported.

---

## worst_pair

The leakage measures compare |0_L> against |1_L>. This searches a Bloch grid of 58 logical states and
maximises the Chernoff exponent over all pairs.

Control: protected codes return numerical noise only.

| channel | code | worst pair | population axis | axis is worst |
|---|---|---|---|---|
| amplitude damping | repetition | 0.654 | 0.654 | yes |
| amplitude damping | [[4,1,2]] | 0.051 | 0.051 | yes |
| amplitude damping | Hamming | 0.0010 | 0.0010 | yes |
| coherent diagonal | [[4,1,2]] | 0.333 | 0.333 | yes |
| coherent diagonal | Hamming | 0.0003 | 0.0003 | yes |

On this grid the population axis gives the largest value on every leaking code under both channels.

---

## coherent

The same measures under a coherent Z-rotation applied to every qubit. Population TVD at theta = 0.3:

| code | TVD |
|---|---|
| repetition | 0 |
| [[4,1,2]] | 3.19e-01 |
| Hamming [[7,1,3]] | 7.63e-03 |
| Steane, five-qubit | ~1e-16 |

Repetition has only Z-type stabilizers; the diagonal error commutes with them and the syndrome does not
move.

Controls: dephasing and depolarizing both give exactly 0. The leak is second order in the angle,
TVD/theta^2 holding near 3.99 as theta goes to zero (0.00997 at 0.05, 0.0395 at 0.1, 0.152 at 0.2).

At theta = 0.2 the Chernoff exponent is 0.153 nats per shot and the attack reaches 1 percent error in 31
rounds.

A coherent Z-rotation is a diagonal unitary, so this case falls under Hu, Liang and Calderbank
(arXiv:2109.13481), who give these probabilities in closed form and the condition for them not to depend
on the encoded state. The amplitude-damping runs are outside that setting. `hlc.py` implements their
equations 45, 48 and 91, and `tests/test_hlc.py` checks the closed form against this exact simulation on the
four CSS codes at theta 0.1, 0.3 and 0.7 for four logical states, to 1e-12.

---

## structure

Whether leakage follows from the code parameters [[n,k,d]] or from finer stabilizer structure.

| code | parameters | analytic order |
|---|---|---|
| Hamming [[7,1,3]] | [[7,1,3]] | 3 |
| Steane [[7,1,3]] | [[7,1,3]] | none |
| Hamming-CSS self-dual | [[7,1,3]] | none |
| Shor [[9,1,3]] | [[9,1,3]] | 3 |

Hamming leaks and Steane does not, though the two have the same parameters. In this set, Steane and the
self-dual Hamming-CSS code have Z generators equal to their X generators with X replaced by Z, and show no
leak. The built-in Hamming code has three generators of each type, the same count as Steane: its X
generators have weights 4, 4, 4 and its Z generators 7, 3, 3. Shor pairs two weight-6 X generators with six
weight-2 Z generators. It is built through the strings-only path, with distance 3 and analytic order 3.

The Shor order is analytic only. The analytic order is compared with exact simulation on codes up to
seven qubits; at nine qubits the projector construction is not run.

---

## device

Leak and rounds-to-error with the channel built from measured device parameters.

Control: setting T1 to infinity, leaving only the T2 phase-damping part, drops the repetition leak to
3.00e-15.

| code | population TVD per round | rounds to 1 percent |
|---|---|---|
| repetition | 1.820e-02 | 251 |
| [[4,1,2]] | 1.473e-04 | 67292 |
| Hamming [[7,1,3]] | 8.936e-07 | 9.6e9 |
| Steane, five-qubit | ~1e-16 | none |

These counts are in the independent-shot regime, where each round is a fresh preparation of the same
logical state.

---

## held_memory

A logical memory holds one state across rounds and extracts syndromes from it each round.
This evolves the ensemble exactly across rounds, with recovery applied each round, at device parameters.

Control: a dephasing channel gives per-round TVD exactly 0 at every round.

| code | leak order | partial sum at 300 rounds | attack error bound |
|---|---|---|---|
| repetition | 1 | 5.42 nats | 0.0022 |
| [[4,1,2]] | 2 | 0.058 nats | 0.472 |
| Hamming [[7,1,3]] | 3 | 3.2e-07 nats | 0.500 |

For repetition the per-round leak goes from 1.82e-2 to 1.54e-2 across 1500 rounds. The re-preparation
case reaches 1 percent at 251 rounds.

The cumulative exponent does not converge on this horizon: the increment over the first 100 rounds is 1.83 nats
and over the last 100 rounds of 1500 it is 1.56 nats. Every figure here is a partial sum at a stated
round count, not a total.

---

## audit

Two checks on the machinery itself.

The attack against its closed form, one shot, 200000 trials:

| case | theory (1 - TVD)/2 | simulated |
|---|---|---|
| repetition, amplitude damping | 0.26000 | 0.26056 |
| [[4,1,2]], amplitude damping | 0.44880 | 0.45066 |
| [[4,1,2]], coherent diagonal | 0.34059 | 0.34012 |
| Hamming, amplitude damping | 0.49130 | 0.49080 |

The Chernoff exponent is a minimisation over a grid. Varying the grid from 51 to 2001 points moves the
value from 0.00100229 to 0.00100234. The default is 201 points.

---

## kl_blocks

The Knill-Laflamme matrix of each code under amplitude damping, computed two ways. The branch matrices are
P_C A_e^dagger A_e P_C for every Kraus product A_e, as in Leung, Nielsen, Chuang and Yamamoto (1997); their
largest eigenvalue gap over branches is the branch spread. The syndrome blocks resolve the same matrix by
syndrome, B_s[i, j] = Tr(Pi_s E(|j_L><i_L|)), and half the sum of |B_s[0,0] - B_s[1,1]| is the population
TVD. Orders are log-log slopes over gamma 0.005, 0.01 and 0.02.

Control: the no-jump branch of the [[4,1,2]] code at gamma 0.1 against equation 39 of Leung et al.

| source | eigenvalues of P_C A^dagger A P_C |
|---|---|
| this package | 0.810000000000, 0.828050000000 |
| Leung et al. eq. 39 | 0.810000000000, 0.828050000000 |

| code | analytic order | syndrome slope | branch spread slope |
|---|---|---|---|
| repetition | 1 | 0.99 | 0.99 |
| [[4,1,2]] | 2 | 1.98 | 1.99 |
| Hamming [[7,1,3]] | 3 | 2.97 | 2.98 |
| Steane [[7,1,3]] | none | none | 2.98 |
| five-qubit [[5,1,3]] | none | none | 5.00 |

On the three leaking codes the three columns agree. On Steane and the five-qubit code the branch spread is
nonzero, at orders 3 and 5, and the syndrome blocks have equal diagonals. The branch spread orders equal the
amplitude-damping population distances in `leak_order`.

---

## hardware

Measured on IBM `ibm_fez`. A 3-qubit repetition code with one round of Z-stabilizer
extraction onto two ancillas, prepared in |0_L> and |1_L>, at four idle delays. Median T1 133.2 us, 4000
shots per circuit. Raw data in `results/hardware_ibm_fez.json`, job metadata in
`results/hardware_ibm_fez_job.json`.

Preparing |1_L> requires X gates that |0_L> does not, so preparation and readout asymmetry contribute to
the measured distance at every delay. The idle-delay sweep separates the two: an amplitude-damping leak
grows with delay, an asymmetry offset does not. The zero-delay point measures the offset.

| delay (us) | gamma | syndrome TVD | Chernoff | 1-shot attack |
|---|---|---|---|---|
| 0 | 0 | 0.0140 | 0.0014 | 0.4930 |
| 20 | 0.1394 | 0.3412 | 0.1198 | 0.3296 |
| 50 | 0.3130 | 0.5888 | 0.3147 | 0.2055 |
| 100 | 0.5280 | 0.7110 | 0.4480 | 0.1435 |

The offset at zero delay is 0.0140 and the distance rises to 0.7110 at 100 us.

Measured against the simulated ideal channel at matched gamma:

| delay (us) | gamma | measured | simulated | difference |
|---|---|---|---|---|
| 0 | 0 | 0.0140 | 0 | +0.0140 |
| 20 | 0.1394 | 0.3412 | 0.3600 | -0.0187 |
| 50 | 0.3130 | 0.5888 | 0.6451 | -0.0563 |
| 100 | 0.5280 | 0.7110 | 0.7476 | -0.0366 |

Measured values are below simulated at every nonzero delay. The simulated model has no ancilla readout
error and no gate error.

Raw syndrome distributions over (00, 01, 10, 11):

| delay (us) | state | 00 | 01 | 10 | 11 |
|---|---|---|---|---|---|
| 0 | \|0_L> | 0.9505 | 0.0158 | 0.0262 | 0.0075 |
| 0 | \|1_L> | 0.9445 | 0.0297 | 0.0205 | 0.0053 |
| 20 | \|0_L> | 0.9560 | 0.0150 | 0.0262 | 0.0027 |
| 20 | \|1_L> | 0.6148 | 0.1510 | 0.1348 | 0.0995 |
| 50 | \|0_L> | 0.9623 | 0.0135 | 0.0230 | 0.0013 |
| 50 | \|1_L> | 0.3735 | 0.2263 | 0.2052 | 0.1950 |
| 100 | \|0_L> | 0.9600 | 0.0147 | 0.0235 | 0.0018 |
| 100 | \|1_L> | 0.2490 | 0.2495 | 0.2507 | 0.2507 |

The |0_L> distribution is flat across delays. The |1_L> distribution moves from 0.9445 on the trivial
syndrome at zero delay to approximately uniform at 100 us.

### Analysis

Output of `analysis_hardware.py`, in `results/hardware_analysis.txt`:

Sampling error, by resampling both distributions at the shot count:

| delay (us) | measured | bootstrap SE |
|---|---|---|
| 0 | 0.0140 | 0.0031 |
| 20 | 0.3412 | 0.0082 |
| 50 | 0.5888 | 0.0082 |
| 100 | 0.7110 | 0.0074 |

Null floor. Two independent 4000-shot samples drawn from one distribution give a mean distance of 0.0052,
a 95th percentile of 0.0100, and a maximum of 0.0190 over 4000 repetitions. The zero-delay distance of
0.0140 is 2.7 times the null mean, p = 0.005.

T1 recovered from the leak. Fitting `measured = a * simulated(gamma(t, T1))` over the three nonzero delays,
with `a` a constant attenuation:

| quantity | value |
|---|---|
| T1 fitted from the syndrome leak | 138.5 us |
| device median T1 from calibration | 133.2 us |
| ratio | 1.040 |
| attenuation a | 0.945 |
| rms residual | 0.0089 |

The fitted T1 is 4.0 percent above the device median. The rms residual is 0.0089 and the bootstrap
standard error is about 0.008. The per-delay ratios of measured to simulated are 0.948, 0.913 and 0.951.

Concerns and limits:

- The circuit ran on qubits chosen by the transpiler and the layout was not recorded, so the comparison
  uses the device median T1 across 156 qubits. Qubit-to-qubit variation on this device is wide, so the
  4 percent agreement should be read against that spread.
- Four delay points and two fitted parameters leave two degrees of freedom. The fit is consistent with
  amplitude damping and has limited power to exclude an additional mechanism of similar shape.
- The zero-delay offset is 0.0140 at p = 0.005, against 0.7110 at 100 us.
- One code, one round of extraction, one backend. The measurement covers the amplitude-damping population
  leak. It leaves the coherent channel, the held-memory regime, and other codes untested on hardware.
