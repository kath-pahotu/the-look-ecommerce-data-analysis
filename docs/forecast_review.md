# Forecast review

*A line-by-line audit of `src/forecasting.py`, run October 2026, before the
module was presented anywhere.*

The forecasting module had been written and was running inside the pipeline,
but it had never been reviewed to the standard of the rest of the project. It
was therefore held back under *Next steps* rather than shown. This document is
the review that released it.

Seven checks were specified before any of them were run, so the list is not a
record of what happened to be found. Two found a defect, two tested a
hypothesis that turned out to be wrong, and three passed.

| # | Check | Result |
|---|---|---|
| 1 | Does the backtest test the horizon the model is run at? | **defect - fixed** |
| 2 | Does the log back-transform bias Holt-Winters low? | hypothesis rejected |
| 3 | Does MAPE's asymmetry distort the ranking? | hypothesis rejected |
| 4 | Is the ranking stable, or an artefact of too few folds? | **defect - fixed** |
| 5 | Does the drift clip `[0.5, 2.5]` ever bind? | pass - never binds |
| 6 | Is the incomplete final month excluded? | pass |
| 7 | Does the country allocation reconcile to the total? | pass - exact |

---

## 1 · The backtest tested a horizon the model is never run at

**What it did.** `backtest()` called each model with `fn(history, 1)` - one
month ahead - at six rolling origins, and ranked by the mean of those six
absolute percentage errors. The production forecast then ran the winner from
May to December 2024: **eight months ahead.**

**Why that matters.** Forecast error grows with horizon, and it does not grow
at the same rate for every method. A rule that carries last year's shape
forward degrades slowly; a fitted trend-and-seasonality model compounds its
trend error every step. Scoring at step one measures the first of those and
says nothing about the second.

Scored across all 32 usable origins, at every step from one to eight:

| Step ahead | `seasonal_naive_drift` | `holt_winters_log` | `seasonal_naive` |
|---|---|---|---|
| 1 | 7.1% | 11.8% | 43.4% |
| 2 | 7.6% | 20.4% | 43.1% |
| 3 | 6.4% | 25.2% | 43.2% |
| 4 | 7.6% | 31.2% | 43.2% |
| 5 | 7.6% | 39.0% | 43.1% |
| 6 | 9.0% | 47.0% | 43.2% |
| 7 | 10.6% | 54.4% | 43.6% |
| 8 | 11.4% | **62.7%** | 44.3% |

At one month the two serious candidates are 7.1% and 11.8% - close enough to
argue about. At eight months they are 11.4% and 62.7%. `holt_winters_log`
degrades by a factor of 5.3 across the horizon; `seasonal_naive_drift` by 1.6.

**The honest version of this finding.** The original design did **not** select
the wrong champion - `seasonal_naive_drift` wins on both scorings. But it had
almost no power to tell the candidates apart. Over its six one-step origins the
two models split the folds three-three:

| Origin | `holt_winters_log` | `seasonal_naive_drift` |
|---|---|---|
| 2023-11 | 0.3% | 4.3% |
| 2023-12 | 5.4% | 5.5% |
| 2024-01 | 16.7% | 9.8% |
| 2024-02 | 19.5% | 19.0% |
| 2024-03 | 24.9% | 4.5% |
| 2024-04 | 13.4% | 16.1% |

A coin flip decided by an average of six numbers. It happened to land on the
model that is right at the horizon used; it could as easily have landed on the
one that is five times worse there.

**Fix.** `backtest()` now takes the production horizon and scores every step
from 1 to `horizon` at every origin. `run()` computes the horizon first and
passes it in, so the two can no longer drift apart.

---

## 2 · The log back-transform - hypothesis rejected

**The concern.** `holt_winters_log` fits on `log(net_sales)` and returns
`np.exp(forecast)`. Exponentiating a mean of logs gives the **median** of the
original distribution, not the mean, so it under-forecasts by roughly
`exp(sigma^2 / 2)`. This is a standard and frequently-missed error.

**What the data says.** At one month over six origins, `holt_winters_log` had a
bias of **+0.6%** - effectively unbiased. The log-space residual variance on
this series is small enough that the correction factor is negligible.

**Conclusion.** Real concern, correctly raised, does not apply here. No smearing
correction added. If the module is ever pointed at a noisier series, the check
should be repeated, because the bias scales with residual variance.

---

## 3 · MAPE's asymmetry - hypothesis rejected

**The concern.** MAPE divides by the actual, so a forecast that is too low is
capped at 100% error while one that is too high is not. It therefore prefers
models that under-predict. If the chosen model under-predicts, the metric may
be choosing it for the wrong reason.

**What the data says.** The same six folds, scored four ways:

| Model | MAPE | sMAPE | RMSE% | Median APE |
|---|---|---|---|---|
| `seasonal_naive_drift` | 9.9% | 10.4% | 11.5% | 7.6% |
| `holt_winters_log` | 13.4% | 13.2% | 15.7% | 15.0% |
| `seasonal_naive` | 54.0% | 74.4% | 54.4% | 53.5% |

All four metrics produce the identical ranking. The choice is not an artefact
of the metric.

**Conclusion.** Hypothesis tested and rejected. MAPE retained, because it is
the metric a commercial audience reads without explanation.

---

## 4 · Six folds was too few

Six origins producing six numbers, with the two candidates splitting them
three-three, is not a selection - it is noise with a winner printed at the
bottom. Re-scored as 6 rolling windows across all 32 origins,
`seasonal_naive_drift` wins **27 of 27 windows** and 29 of 32 individual
origins, so the conclusion is robust. But that was established by this review,
not by the code.

**Fix.** `BACKTEST_MONTHS = 6` is replaced by `BACKTEST_ORIGINS = 24`, capped at
run time by what the series can support while leaving
`2 * SEASONAL_PERIODS + 1` months for the fit. The production backtest now runs
24 origins x 8 steps = **192 folds** instead of 6, and every one of them is
written to `mart.forecast_backtest_detail` so the horizon decay can be queried
rather than trusted.

### What the champion looks like after the fix

| Model | MAPE (8-step) | Step 1 | Step 8 | Bias | Worst fold |
|---|---|---|---|---|---|
| **`seasonal_naive_drift`** | **8.0%** | 6.5% | 11.5% | -0.7% | 39% |
| `holt_winters_log` | 26.0% | 8.3% | 43.5% | +8.3% | 163% |
| `seasonal_naive` | 42.4% | 41.7% | 44.2% | -42.4% | 65% |

`holt_winters_log` is also the unstable one: its worst single origin reaches
163%, against 39% for the champion. On a series growing this fast, a fitted
trend occasionally extrapolates badly, and eight months is long enough for that
to compound.

---

## 5 · The drift clip never binds

`seasonal_naive_drift` multiplies last year's shape by the latest year-on-year
ratio, clipped to `[0.5, 2.5]`. Clipping an input without checking whether the
clip is active hides the cases where it changed the answer.

Across 12 origins the raw ratio ranged from **1.54 to 2.39** and the clip bound
**0 times**. It is a guard against a pathological input, not a silent
adjustment to normal ones.

Worth noting separately: a drift ratio around 2.0 means net sales roughly double
year on year. That is a property of the synthetic dataset, not of retail.

---

## 6 · The incomplete month is excluded - pass

`mart.sales_monthly` carries an `is_complete_month` flag, and May 2024 is
flagged incomplete: 6,556 orders against 8,703 in April. Had it been included,
it would have corrupted both the final backtest fold and the forecast origin.

The query already reads `WHERE is_complete_month = 1`. The series ends at April
2024, which is also why the horizon is eight months rather than seven.

---

## 7 · The country allocation reconciles exactly - pass

The global forecast is allocated to markets on each market's trailing six-month
share of net sales. A top-down split must sum back to the total it was split
from, so:

```sql
SELECT f.month_start,
       f.forecast_net_sales_usd                       AS total,
       SUM(a.forecast_net_sales_usd)                  AS allocated,
       SUM(a.forecast_net_sales_usd)
         - f.forecast_net_sales_usd                   AS delta
FROM mart.forecast_monthly f
JOIN mart.forecast_country_month a USING (month_start)
GROUP BY 1, 2
```

Maximum absolute delta across all eight months: **0.000000**.

---

## What is still true after the review

These are limitations, not defects. They are stated here so they are stated
somewhere other than in conversation.

**TheLook is synthetic.** Its growth curve is far smoother than real demand,
which carries promotional spikes, stockouts and competitive shocks. An 8.0%
MAPE here is a demonstration of a validation method, not an accuracy claim that
transfers to a real business.

**The plan is constructed.** TheLook ships no budget data, so
`src/build_plan_source.py` generates the plan from a documented, deterministic
rule. `mart.forecast_vs_plan` therefore compares a real forecast against a
synthetic target. Every number derived from it inherits that.

**This is univariate.** There is no marketing spend, no price change and no
promotion in the data, so nothing drives the forecast except the series' own
history. That is not a flaw if it is read correctly: a statistical baseline is
what a commercial plan should be challenged against. "The plan assumes 20%
growth; the series alone supports 8%; the remaining 12 points need a named
driver" is the sentence this module is for.

**The benchmark is weak.** `seasonal_naive` under-predicts in every fold
(bias -42%) because the series nearly doubles year on year. It proves the other
models beat a naive rule; it does not prove they are good.

---

## Reproducing this review

Every number above comes from the warehouse and can be re-derived:

```python
from src.explore import open_warehouse
w = open_warehouse()

w.peek("mart.forecast_accuracy")             # the scores table
w.q("""SELECT step, model, AVG(absolute_percentage_error) AS mape
       FROM mart.forecast_backtest_detail
       GROUP BY 1, 2 ORDER BY 1, 3""")       # the horizon decay in check 1
w.source("mart.forecast_monthly")            # the SQL that builds it
```

Section 9 of `notebooks/90_workbench.ipynb` runs all seven checks end to end.
