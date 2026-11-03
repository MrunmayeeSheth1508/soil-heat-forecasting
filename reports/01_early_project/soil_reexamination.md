# Soil Heat Candidate: Re-examination of the Closure

Scripts: `soil/09_amplitude_check.py`, `soil/10_windowed_alpha.py`. Outputs: `amp_check_out.txt`, `windowed_out.txt`.

## 1. Was D fitted or fixed? (code review of `04b_shallow_pilot.py`)

**Fitted.** `alpha` was fitted per episode on the first two-thirds (Nelder-Mead on log alpha, one start at log alpha = -13), then used on the last third. It was not a textbook value. Two weaknesses: single start point, and SSE fitted only on the calibration third.

## 2. Is the solver right? (computed)

Compared with the exact periodic analytic solution for alpha from 2e-7 to 1.2e-6 m^2/s: amplitude error 0.06 to 1.0 percent at the pilot time step (about 0.6 to 1.4 percent with 6 sub-steps), phase error under 0.02 h. **The solver is not the cause.**

## 3. Does the amplitude error vanish when alpha is fitted in-sample? (computed)

| Fit | Amplitude ratio model/obs |
|---|---|
| Pilot: calibration third, tested on last third of episode 4 | about 1.33 (the "33 percent") |
| Episode 4, whole-episode min-RMSE alpha | 1.095 |
| 10 episodes of 144 h or more, whole-episode min-RMSE alpha | median 1.076, range 0.876 to 1.152 |
| 276 windows of 96 h, per-window alpha | median 1.085, 10th to 90th percentile 1.008 to 1.176 |

Phase error under 0.7 h in every episode. Whole-episode RMSE 0.15 to 0.47 C.
Episode 4 alpha scan: as alpha grows the amplitude ratio saturates near 1.30, so a ratio near 1.33 is what a too-large or poorly transferred alpha gives, not evidence of structure.

**Conclusion: most of the 33 percent was a calibration-to-validation transfer failure on one episode, not structural misspecification.** A residual misfit of roughly 5 to 15 percent in amplitude remains after fitting.

## 4. Solver-free harmonic check (computed, 575 daily windows)

| Layer | alpha from amplitude / alpha from phase (median) | IQR |
|---|---|---|
| 5 to 10 cm | 0.44 | 0.26 to 0.83 |
| 10 to 20 cm | 1.01 | 0.76 to 1.47 |
| 5 to 20 cm | 0.74 | 0.59 to 1.17 |

Homogeneous 1D conduction needs this ratio to be 1. It holds for 10 to 20 cm and fails for 5 to 10 cm. The remaining misfit sits in the top layer.
**Probe aggregation is consistent with this but not demonstrated.** Layering, near-surface vapour or latent-heat effects, and sensor placement would produce the same pattern. I did not test any of them.

## 5. The moisture null (code review plus computed)

In the pilot, `b = np.exp(params[1])` forces the moisture coefficient to be **positive**. The reported collapse of beta to about 1e-18 is what a one-sided optimiser does if the data prefer a negative slope.

Windowed alpha (276 windows, 14 episodes) against window-mean covariates, Spearman correlation:

| Covariate | Pooled rho | Within-episode rho |
|---|---|---|
| Soil moisture 5 cm | -0.30 | -0.32 |
| Soil moisture 10 cm | -0.27 | -0.22 |
| Soil moisture 20 cm | -0.10 | -0.14 |
| Mean temperature 10 cm | +0.54 | +0.48 |

Alpha falls as soil gets wetter and rises with temperature. Caveats: windows overlap by 50 percent and are autocorrelated, so the p-values are overstated; moisture and temperature co-vary in dry-down periods so they are not separated; the variance of log alpha is modest (within-episode 0.034).
Episode count check: 14 episodes of 144 h or more with valid temperature and moisture, as in the pilot. My regex for the pilot table returned 0 rows, which is a parsing failure of my check, not evidence.

## 6. Verdict

| Earlier claim | Status now |
|---|---|
| Base model overpredicts amplitude by 33 percent, so it is misspecified | **Overstated.** Mostly a transfer failure; about 8 percent after fitting |
| Cause is probe aggregation | **Untested** |
| Moisture coefficient is not identified | **Not established.** Test was sign-constrained |
| Soil candidate closed | **Premature. Reopened** |

## 7. Proposed next test

Refit with signed moisture coefficient and a temperature covariate. Calibrate on some episodes, test on whole withheld episodes. Compare against constant alpha. Keep 20 cm out of calibration as before.
