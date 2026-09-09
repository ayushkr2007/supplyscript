"""
SupplyPrescript - Week 3, Day 6: Before/After Calibration Comparison
--------------------------------------------------------------------------
Day 5 fit an isotonic calibrator and re-ran the batch through the same
optimizer, producing data/week3_day5_calibrated_prescriptions.json.
16/200 orders got a different decision, and expected_loss_before rose
from $7,451 to $7,597.81 (a more honest risk estimate, not a bug).

But a decision change and a higher headline loss number don't by
themselves prove the fix HELPED. This script re-runs Day 2's
precision/recall/wasted-spend eval and Day 4's calibration check on
BOTH files -- original prescriptions.json and the Day 5 calibrated
version -- and prints them side by side, so the improvement (or lack
of one) is measured, not assumed.

Same honesty caveat as every prior day: retrospective check against
historical ground truth on this 200-order sample, not a live experiment.
"""

import json
import pandas as pd

DATA_DIR = "data"
ORIGINAL_PATH = f"{DATA_DIR}/prescriptions.json"
CALIBRATED_PATH = f"{DATA_DIR}/week3_day5_calibrated_prescriptions.json"
N_BINS = 10


def load_true_labels(n_orders: int = 200, seed: int = 1) -> pd.Series:
    """Reproduce the exact sample used by prescribe_batch() so
    order_id aligns with the correct ground-truth label."""
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()
    sampled_idx = X_test.sample(n=n_orders, random_state=seed).index
    return y_test.loc[sampled_idx].reset_index(drop=True)


def load_prescriptions(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def evaluate_targeting(orders: list, true_labels: pd.Series) -> dict:
    """Same logic as Day 2: precision/recall/wasted-spend/missed-value."""
    n_orders = len(orders)
    acted_on = [o for o in orders if o["decision"] in ("upgrade", "discount")]
    skipped = [o for o in orders if o["decision"] == "nothing"]

    acted_true_late = sum(1 for o in acted_on if true_labels.iloc[o["order_id"]] == 1)
    precision = acted_true_late / len(acted_on) if acted_on else 0
    total_truly_late = sum(1 for i in range(n_orders) if true_labels.iloc[i] == 1)
    recall = acted_true_late / total_truly_late if total_truly_late else 0
    wasted_spend = sum(o["cost"] for o in acted_on if true_labels.iloc[o["order_id"]] == 0)
    total_spend = sum(o["cost"] for o in acted_on)
    missed_value = sum(o["value_at_risk"] for o in skipped if true_labels.iloc[o["order_id"]] == 1)

    return {
        "n_acted_on": len(acted_on),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "total_spend": round(total_spend, 2),
        "wasted_spend": round(wasted_spend, 2),
        "wasted_spend_pct": round(wasted_spend / total_spend * 100, 1) if total_spend else 0,
        "missed_value": round(missed_value, 2),
    }


def evaluate_calibration(orders: list, true_labels: pd.Series) -> dict:
    """Same logic as Day 4: Brier score + Expected Calibration Error."""
    df = pd.DataFrame([{"order_id": o["order_id"], "risk_score": o["risk_score"]} for o in orders])
    df["actual_late"] = df["order_id"].apply(lambda i: int(true_labels.iloc[i]))

    brier_score = ((df["risk_score"] - df["actual_late"]) ** 2).mean()

    df["bin"] = pd.cut(df["risk_score"], bins=N_BINS, include_lowest=True)
    ece_weighted_sum = 0.0
    for _, group in df.groupby("bin", observed=True):
        if len(group) == 0:
            continue
        gap = group["actual_late"].mean() - group["risk_score"].mean()
        ece_weighted_sum += abs(gap) * len(group)
    ece = ece_weighted_sum / len(df)

    return {"brier_score": round(brier_score, 4), "ece": round(ece, 4)}


def pct_change(before, after):
    if before == 0:
        return None
    return round((after - before) / abs(before) * 100, 1)


def main():
    original = load_prescriptions(ORIGINAL_PATH)
    calibrated = load_prescriptions(CALIBRATED_PATH)
    n_orders = len(original["orders"])
    true_labels = load_true_labels(n_orders=n_orders)

    before_t = evaluate_targeting(original["orders"], true_labels)
    after_t = evaluate_targeting(calibrated["orders"], true_labels)
    before_c = evaluate_calibration(original["orders"], true_labels)
    after_c = evaluate_calibration(calibrated["orders"], true_labels)

    rows = [
        ("Precision", f"{before_t['precision']*100:.1f}%", f"{after_t['precision']*100:.1f}%"),
        ("Recall", f"{before_t['recall']*100:.1f}%", f"{after_t['recall']*100:.1f}%"),
        ("Wasted spend", f"${before_t['wasted_spend']}", f"${after_t['wasted_spend']}"),
        ("Wasted spend %", f"{before_t['wasted_spend_pct']}%", f"{after_t['wasted_spend_pct']}%"),
        ("Missed value", f"${before_t['missed_value']}", f"${after_t['missed_value']}"),
        ("Brier score", f"{before_c['brier_score']}", f"{after_c['brier_score']}"),
        ("Calibration error (ECE)", f"{before_c['ece']}", f"{after_c['ece']}"),
    ]

    print(f"Before/after comparison -- {n_orders} orders")
    print()
    print(f"{'Metric':<26}{'Before (original)':>20}{'After (calibrated)':>22}")
    for label, before, after in rows:
        print(f"{label:<26}{before:>20}{after:>22}")
    print()

    brier_delta = pct_change(before_c["brier_score"], after_c["brier_score"])
    ece_delta = pct_change(before_c["ece"], after_c["ece"])
    wasted_delta = pct_change(before_t["wasted_spend"], after_t["wasted_spend"])
    missed_delta = pct_change(before_t["missed_value"], after_t["missed_value"])

    print("Deltas:")
    print(f"  Brier score:  {brier_delta:+.1f}% ({'improved' if brier_delta < 0 else 'worsened'})")
    print(f"  ECE:          {ece_delta:+.1f}% ({'improved' if ece_delta < 0 else 'worsened'})")
    print(f"  Wasted spend: {wasted_delta:+.1f}% ({'improved' if wasted_delta < 0 else 'worsened'})")
    print(f"  Missed value: {missed_delta:+.1f}% ({'improved' if missed_delta < 0 else 'worsened'})")
    print()
    print("NOTE: retrospective check against historical ground truth on this")
    print("200-order sample, not a live experiment -- see prior days' caveats.")

    result = {
        "n_orders": n_orders,
        "before": {**before_t, **before_c},
        "after": {**after_t, **after_c},
        "deltas_pct": {
            "brier_score": brier_delta,
            "ece": ece_delta,
            "wasted_spend": wasted_delta,
            "missed_value": missed_delta,
        },
    }
    with open(f"{DATA_DIR}/week3_day6_before_after.json", "w") as f:
        json.dump(result, f, indent=2)
    print()
    print(f"Saved to {DATA_DIR}/week3_day6_before_after.json")


if __name__ == "__main__":
    main()
