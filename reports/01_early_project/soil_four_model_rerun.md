# Soil Heat Candidate: Corrected Four-Model Rerun

Script: `soil/12_four_model_rerun.py` (design and decision rule fixed in its header before any result). Output: `soil/rerun_out.txt`. Episode table: `soil/episode_table_out.txt`.

## Design (as specified)

- Shallow 5-20 cm model; T5 and T20 are boundary inputs; T10 is never an input (target only).
- alpha = exp[a + b(theta - theta0) + c(Tin - T0)], b and c signed. A: constant. B: moisture. C: temperature. D: both.
- theta = measured 10 cm moisture (explicit representative-layer assumption).
- Tin = trailing 24 h mean of (T5 + T20)/2. Uses boundary observations only.
- Centres from training episodes only. Equal weight per episode. First 24 h of each episode discarded.
- Episodes 1-11 (Jan 2019 to Oct 2020) for training and leave-one-episode-out (LOEO). Episodes 12-14 (Oct 2020 to Jan 2021) scored once as the final test.

## Confounding in the data (computed before fitting)

| Quantity | Value |
|---|---|
| Hourly correlation, moisture vs layer temperature (all 14 episodes) | -0.59 |
| Correlation of episode means, moisture vs temperature | -0.87 |
| Training hourly correlation of theta and Tin | -0.61 |

Wet episodes are cold episodes. Moisture and temperature are largely the same seasonal signal in this record.

## Results

**Training fit, mean per-episode RMSE of T10 (C):** A 0.421, B 0.418, C 0.409, D 0.408.

| Model | Fitted coefficients | alpha change across training IQR |
|---|---|---|
| B | b = -0.131 per 0.1 m3/m3 | x0.83 over theta |
| C | c = +0.279 per 10 C | x1.48 over Tin |
| D | b = +0.147, c = +0.409 | x1.24 over theta, x1.77 over Tin |

**Moisture slope changes sign once temperature is included** (B: -0.131, D: +0.147).

**LOEO on training episodes (held-out RMSE, mean of 11):** A 0.394, B 0.388, C 0.377, D 0.382.

| Comparison | Better in | Mean improvement (C) | Bootstrap 95% CI |
|---|---|---|---|
| B vs A | 8/11 | +0.0056 | -0.0077 to +0.0170 |
| C vs A | 8/11 | +0.0173 | +0.0019 to +0.0317 |
| D vs B | 6/11 | +0.0065 | -0.0077 to +0.0212 |
| **D vs C (decisive)** | **5/11** | **-0.0052** | **-0.0118 to +0.0009** |

**Episode bootstrap (200 resamples, 11 training episodes):**

| Model | Parameter | Median | 95% interval | Fraction with expected sign |
|---|---|---|---|---|
| B | b | -0.157 | -0.396 to +0.048 | 0.92 negative |
| C | c | +0.300 | +0.115 to +0.462 | 1.00 positive |
| D | b | +0.113 | -0.157 to +0.424 | 0.22 negative |
| D | c | +0.405 | +0.129 to +0.726 | 0.99 positive |

Bootstrap correlation of b and c in D: **+0.81** (strong compensation).

**Final untouched test (RMSE, C):**

| Episode | A | B | C | D |
|---|---|---|---|---|
| 12 | 0.514 | 0.519 | 0.521 | 0.521 |
| 13 | 0.195 | 0.199 | 0.215 | 0.226 |
| 14 | 0.234 | 0.233 | 0.266 | 0.283 |

On the test set, D beats C in 0/3 episodes. C beats A in 0/3 episodes. A is best or tied in all three. In episode 14, C and D bring the amplitude ratio closer to 1 (A 1.12, C 1.04, D 1.03) but worsen phase error (A -0.26 h, C -0.69 h, D -0.78 h) and total RMSE.

## Pre-specified decision rule (D vs C)

| Criterion | Result |
|---|---|
| (i) LOEO: D better in 8 or more of 11 and CI excludes 0 | 5/11, CI includes 0: **fail** |
| (ii) Test: D better in all 3 | 0/3: **fail** |
| (iii) Bootstrap interval for b excludes 0 | [-0.157, +0.424]: **fail** |

**Verdict: a moisture effect is not established beyond temperature.**

## What this does and does not show

- The earlier negative moisture slope is explained by temperature in this record: with temperature in the model, b changes sign and its interval spans zero. This is consistent with confounding, not proof of it.
- b and c are strongly compensating (+0.81), so the data cannot separate the two effects. The moisture effect is **unidentified**, not shown to be absent.
- Temperature dependence has modest support in cross-validation (C vs A CI excludes 0, improvement 0.017 C) but does not reproduce on the final three episodes. The test episodes are all autumn to winter, and 3 episodes give little power.
- All model differences (0.005 to 0.03 C) are small against both the 0.1 C reporting resolution and the episode-to-episode RMSE range (0.19 to 0.81 C). The dominant error is something none of the four models represents. Warm-season episodes show the largest errors (episodes 3, 4, 9, 10: 0.5 to 0.8 C).
- The amplitude and phase behaviour in episode 14 is the same top-layer inconsistency found in the harmonic check: no single alpha matches both.

## Limits of this test

- 11 training episodes; episode bootstrap is crude. Episodes 2, 5 and 8 are long (about 2,600 to 3,400 h) but weighted equally with 220 h episodes.
- Single station (Selma, AL); one soil and one climate.
- Moisture is a 10 cm sensor value used as a layer representative. Within many episodes its range is small.
- Linear-in-log dependence; other forms not tried.

## Status

| Item | Status |
|---|---|
| Old moisture null (sign-constrained) | Invalidated |
| Moisture effect beyond temperature | **Not established; unidentified** (collinearity, compensation) |
| Temperature effect | Weak: supported in LOEO, fails final test |
| Base-model misfit | Real but modest, concentrated in the top layer |
