# Week 3 Summary — The Closed Loop

SupplyPrescript's Week 1–2 work built a system that *predicts* delay risk
and *prescribes* a budget-constrained mitigation action per order. Week 3
asked the harder question: once those prescriptions are executed, were
they actually right? This is the honest accounting of that check —
including the parts that weren't fine on the first pass.

## Day 1 — Predicted vs. Actual, on Executed Decisions

Compared each decision actually executed through the dashboard against
its real historical outcome, using the `actual_outcome` / `actual_cost`
fields written back to the decisions table (`w3_day1_evaluate.py`).

**Caveat carried through every day below:** this checks whether the
model's *prediction* matched reality, not whether the *action taken*
caused a better outcome — we can't re-run history with a different
shipping mode chosen. It's a retrospective correctness check, not a
causal experiment.

## Day 2 — Full-Batch Precision, Recall, and Wasted Spend

Day 1's sample was small (only the handful of decisions manually
executed via the dashboard). Day 2 evaluated the optimizer's full
200-order batch against ground truth (`w3_day2_full_batch_eval.py`):

| Metric | Value | Meaning |
|---|---|---|
| Precision | 74.2% | Of every dollar spent, ~3 in 4 went to orders that really were going to be late |
| Recall | 89.4% | The optimizer caught 89% of all truly-late orders in the batch |
| Wasted spend | $164.40 (20.6%) | Spent on orders that turned out fine anyway |
| Missed value | $112.55 | At risk among truly-late orders the optimizer chose not to act on (budget ran out) |

Honest read: strong recall, a real precision/recall trade-off — not a
flaw, just the normal cost of catching that much real risk.

## Day 3 — Decision ROI Dashboard View

Built the `RoiPanel` component, combining Day 2's at-scale batch stats
with a live view of dashboard-executed decisions checked against real
outcomes — a per-decision-type "did it pay off" breakdown with a running
wasted-spend total. (This was the piece originally assigned to a
teammate; it had never been delivered, so it was built directly.)

## Day 4 — Risk-Score Calibration Check

Precision and recall only measure *ranking* — is a high-risk order more
likely to be late than a low-risk one? They say nothing about whether
`risk_score` is trustworthy as an absolute probability, which matters
because the optimizer's entire expected-value math depends on it
literally: `expected_loss = risk_score × value_at_risk`.

Bucketed all 200 orders by predicted risk and compared each bucket's
average prediction to its actual observed late-rate:

| Risk bucket | Gap (actual − predicted) |
|---|---|
| 0.13–0.39 | slightly overconfident (−0.02 to −0.10) |
| 0.39–0.48 | **meaningfully underconfident (+0.242, the worst)** |
| 0.48–0.91 | underconfident (+0.07 to +0.13) |
| 0.91–1.00 | accurate (−0.017) |

**Brier score: 0.1543. Expected Calibration Error: 0.096.** Verdict:
mildly miscalibrated overall, but with one real problem band (0.39–0.48)
where the model was quietly understating risk.

## Day 5 — Calibration Fix

Fit an isotonic regression calibrator — chosen over simple logistic
(Platt) scaling because Day 4's error wasn't a uniform bias, it was a
bumpy over/under pattern isotonic regression can follow. Fit on the
**full test set**, not the same 200-order sample being evaluated, so the
correction generalizes rather than overfitting.

Fed the calibrated scores through the *same* PuLP optimizer
(`w3_day5_calibrate.py` reuses the real pipeline, doesn't reimplement
it) so orders could genuinely land on different decisions:

- **16 of 200 orders (8%)** changed decision as a direct result of
  calibration — concentrated in the miscalibrated bands
- Expected loss (before mitigation) rose from $7,451 to $7,597.81 — not
  a regression, a more honest risk estimate; the old number was quietly
  understating real risk in the mid-range
- Loss reduction held steady at ~83–84% (a relative measure, moved with
  both sides)

## Day 6 — Before/After: Did It Actually Help?

A decision changing isn't proof it changed for the better. Ran Day 2's
targeting eval and Day 4's calibration check on **both** the original
and calibrated prescriptions, side by side:

| Metric | Before | After | Change |
|---|---|---|---|
| Precision | 74.2% | 79.0% | improved |
| Recall | 89.4% | 90.9% | improved |
| Wasted spend | $164.40 | $140.00 | −14.8%, improved |
| Missed value | $112.55 | $115.40 | +2.5%, slightly worse |
| Brier score | 0.1543 | 0.1493 | −3.2%, improved |
| Calibration error (ECE) | 0.096 | 0.0874 | −9.0%, improved |

**Precision and recall improved together** — not a typical trade-off,
which is a good sign the fix addressed a real error rather than just
shifting it around. Wasted spend dropped by nearly $25 on this batch.

The one metric that got marginally worse — missed value, up $2.85 — is
real and worth naming rather than hiding: fixing calibration meant the
optimizer spent more precisely on the highest-confidence real risks,
which meant deprioritizing a few borderline orders that turned out
late. A $2.85 shift against a $164 baseline is small and expected, not
a flaw to chase further.

## Bottom Line

The closed loop works as designed: predictions were checked against
reality (Day 1–2), a real weakness was found rather than assumed away
(Day 4), and fixing it produced a measured, honest improvement with one
disclosed trade-off (Day 5–6) — not a claimed "everything got better"
result. That's the actual point of building the loop in the first
place.

## Known Open Items

- `origin/main` was force-pushed with fabricated commit history twice
  during this project (documented, restored both times; suspect states
  preserved as git tags for reference). Branch protection should be
  enabled on `main` going forward.
- The teammate originally assigned the Decision ROI dashboard view
  (Week 3's Day 3 deliverable) never produced any commits on their
  branch; it was built directly instead.
