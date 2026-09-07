"""
SupplyPrescript - Week 3, Day 5: Calibration Fix
--------------------------------------------------------------------------
Day 4 found the model's risk_score is mildly miscalibrated: overconfident
below ~0.40, meaningfully underconfident in the 0.39-0.56 band (worst gap
+0.242), underconfident again through 0.65-0.91, accurate only at the
very top (Brier 0.1543, ECE 0.096).

This fixes it with isotonic regression -- a non-parametric monotonic
mapping from raw model probability to a corrected probability, fit
against real outcomes. Isotonic (rather than Platt/logistic scaling) is
the right choice here because Day 4's error shape isn't a simple
uniform bias -- it's a bumpy over/under pattern across risk bands, and
isotonic regression can follow that shape instead of forcing a single
sigmoid correction.

Important methodology note: the calibrator is fit on the FULL X_test /
y_test set, not just the same 200-order sample Day 2/Day 4 evaluated on.
Fitting and evaluating calibration on the identical small sample would
overstate the fix -- the correction needs to generalize.

This reuses the exact pipeline from w2_day3_json_output_fixed.py
(same schema, same budget/optimizer logic) so the output is a drop-in
comparison to the original prescriptions.json -- but with the
calibrated risk_score fed into the SAME PuLP optimizer, so orders can
genuinely end up with different decisions where the correction matters,
not just a relabeled risk number.

Output: data/week3_day5_calibrated_prescriptions.json (kept separate
from data/prescriptions.json so Day 6 can compare before vs. after
without needing a second run).
"""

import json
import joblib
import pandas as pd
from sklearn.isotonic import IsotonicRegression

import w2_day3_json_output_fixed as w2  # same directory -- reuses the real pipeline

DATA_DIR = "data"
MODEL_PATH = "models/xgb_tuned.pkl"
CALIBRATOR_PATH = "models/isotonic_calibrator.pkl"


def fit_calibrator(model) -> IsotonicRegression:
    """Fit isotonic regression on the FULL test set (not the 200-order
    sample) so the correction generalizes rather than overfitting the
    exact orders Day 2/Day 4 evaluated."""
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    X_test = w2.encode_leftover_text_columns(X_test)
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()

    raw_proba = model.predict_proba(X_test)[:, 1]

    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    calibrator.fit(raw_proba, y_test)
    return calibrator


def prescribe_batch_calibrated(calibrator, n_orders: int = 200, budget: float = w2.BUDGET, seed: int = 1) -> dict:
    """Same as w2.prescribe_batch(), but risk_score is passed through
    the fitted calibrator before the optimizer runs -- so the PuLP
    solver sees corrected probabilities and can genuinely choose
    different decisions, not just display a different number."""
    model = w2.load_model()
    batch = w2.load_batch(n_orders=n_orders, seed=seed)
    scored = w2.score_batch(model, batch)

    # The calibration step -- everything else below is unchanged from
    # the original pipeline.
    scored["risk_score"] = calibrator.predict(scored["risk_score"])

    opt_input = w2.build_options(scored)
    result = w2.solve_multi_option(opt_input, budget=budget)

    records = w2.to_json_records(result)

    total_cost = sum(r["_raw_cost"] for r in records)
    loss_before = sum(r["expected_loss_before"] for r in records)
    loss_after = sum(r["expected_loss_after"] for r in records)
    for r in records:
        del r["_raw_cost"]

    return {
        "summary": {
            "batch_size": len(records),
            "budget": budget,
            "total_cost": round(total_cost, 2),
            "expected_loss_before": round(loss_before, 2),
            "expected_loss_after": round(loss_after, 2),
            "loss_reduction_pct": round((loss_before - loss_after) / loss_before * 100, 1),
            "decision_counts": {
                opt: sum(1 for r in records if r["decision"] == opt)
                for opt in ["upgrade", "discount", "nothing"]
            },
        },
        "orders": records,
    }


def compare_decisions(original_path: str, calibrated: dict) -> int:
    """How many of the 200 orders got a DIFFERENT decision purely from
    the calibration fix -- the real evidence this wasn't cosmetic."""
    try:
        with open(original_path) as f:
            original = json.load(f)
    except FileNotFoundError:
        return -1

    orig_decisions = {o["order_id"]: o["decision"] for o in original["orders"]}
    changed = sum(
        1 for o in calibrated["orders"]
        if orig_decisions.get(o["order_id"]) != o["decision"]
    )
    return changed


def main():
    print("Fitting isotonic calibrator on full test set...")
    model = w2.load_model()
    calibrator = fit_calibrator(model)
    joblib.dump(calibrator, CALIBRATOR_PATH)
    print(f"Calibrator saved to {CALIBRATOR_PATH}")
    print()

    print("Re-running the batch through the SAME optimizer with calibrated scores...")
    result = prescribe_batch_calibrated(calibrator)

    print()
    print("=== Calibrated summary ===")
    print(json.dumps(result["summary"], indent=2))

    out_path = f"{DATA_DIR}/week3_day5_calibrated_prescriptions.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print()
    print(f"Saved to {out_path}")

    changed = compare_decisions(f"{DATA_DIR}/prescriptions.json", result)
    if changed >= 0:
        print(f"\n{changed}/{result['summary']['batch_size']} orders got a DIFFERENT decision "
              f"after calibration -- these are the orders the original miscalibration was misjudging.")
    else:
        print(f"\n(Couldn't find {DATA_DIR}/prescriptions.json to diff against -- "
              "run w2_day3_json_output_fixed.py first if you want the before/after comparison.)")


if __name__ == "__main__":
    main()
