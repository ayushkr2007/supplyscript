"""
SupplyPrescript - Week 3, Day 4: Risk-Score Calibration Check
--------------------------------------------------------------------------
Day 2 showed the optimizer targets spend reasonably well (74.2% precision,
89.4% recall) -- but precision/recall only care about RANKING: is a
high-risk order more likely to be late than a low-risk one? They say
nothing about whether risk_score is trustworthy as an actual probability.

That matters because the optimizer's entire expected-value math trusts
risk_score literally:

    expected_loss_before = risk_score * value_at_risk

If the model is systematically overconfident (predicts 0.80 when the
real rate at that level is 0.55) or underconfident, every expected-loss
number the dashboard shows -- and every budget-allocation trade-off the
PuLP optimizer makes -- is quietly wrong, even though precision/recall
look fine. This script checks calibration directly: bucket orders by
predicted risk, compare each bucket's average prediction to its actual
observed late-rate.

Same honesty caveat as Day 1/Day 2: retrospective check against
historical ground truth on this 200-order sample, not a live experiment.
"""

import json
import pandas as pd

DATA_DIR = "data"
PRESCRIPTIONS_PATH = f"{DATA_DIR}/prescriptions.json"
N_BINS = 10


def load_true_labels(n_orders: int = 200, seed: int = 1) -> pd.Series:
    """Reproduce the exact sample used by prescribe_batch() so
    order_id aligns with the correct ground-truth label.
    (Identical to Day 2 -- must match for order_id alignment to hold.)"""
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()

    sampled_idx = X_test.sample(n=n_orders, random_state=seed).index
    y_sampled = y_test.loc[sampled_idx].reset_index(drop=True)
    return y_sampled


def load_prescriptions() -> dict:
    with open(PRESCRIPTIONS_PATH) as f:
        return json.load(f)


def check_calibration():
    prescriptions = load_prescriptions()
    orders = prescriptions["orders"]
    n_orders = len(orders)
    true_labels = load_true_labels(n_orders=n_orders)

    df = pd.DataFrame([
        {"order_id": o["order_id"], "risk_score": o["risk_score"]}
        for o in orders
    ])
    df["actual_late"] = df["order_id"].apply(lambda i: int(true_labels.iloc[i]))

    # Brier score: mean squared error between predicted probability and
    # actual outcome (0 = perfect, 0.25 = no better than always guessing 50%)
    brier_score = ((df["risk_score"] - df["actual_late"]) ** 2).mean()

    # Bucket into N_BINS equal-width bins by predicted risk_score
    df["bin"] = pd.cut(df["risk_score"], bins=N_BINS, include_lowest=True)

    bins = []
    ece_weighted_sum = 0.0
    for interval, group in df.groupby("bin", observed=True):
        if len(group) == 0:
            continue
        mean_predicted = group["risk_score"].mean()
        actual_rate = group["actual_late"].mean()
        gap = actual_rate - mean_predicted
        bins.append({
            "range": f"{interval.left:.2f}-{interval.right:.2f}",
            "n": len(group),
            "mean_predicted": round(mean_predicted, 3),
            "actual_rate": round(actual_rate, 3),
            "gap": round(gap, 3),
        })
        ece_weighted_sum += abs(gap) * len(group)

    # Expected Calibration Error: weighted average gap across bins
    ece = ece_weighted_sum / n_orders

    if ece < 0.05:
        verdict = "well-calibrated -- risk_score can be trusted as a real probability"
    elif ece < 0.10:
        verdict = "mildly miscalibrated -- usable, but expected-loss figures carry some error"
    else:
        verdict = "meaningfully miscalibrated -- expected-loss math and budget trade-offs are unreliable at face value"

    return {
        "n_orders": n_orders,
        "brier_score": round(brier_score, 4),
        "expected_calibration_error": round(ece, 4),
        "verdict": verdict,
        "bins": bins,
    }


def main():
    stats = check_calibration()

    print(f"Calibration check: {stats['n_orders']} orders, {N_BINS} bins")
    print()
    print(f"{'Risk bucket':<14}{'n':>5}{'Predicted':>12}{'Actual':>10}{'Gap':>8}")
    for b in stats["bins"]:
        print(f"{b['range']:<14}{b['n']:>5}{b['mean_predicted']:>12.3f}{b['actual_rate']:>10.3f}{b['gap']:>+8.3f}")
    print()
    print(f"Brier score: {stats['brier_score']} (0 = perfect, 0.25 = no better than a coin flip)")
    print(f"Expected Calibration Error: {stats['expected_calibration_error']}")
    print(f"Verdict: {stats['verdict']}")
    print()
    print("NOTE: this checks whether risk_score is trustworthy as an absolute")
    print("probability, not just a good ranking signal -- see module docstring.")

    with open(f"{DATA_DIR}/week3_day4_calibration.json", "w") as f:
        json.dump(stats, f, indent=2)
    print()
    print(f"Saved to {DATA_DIR}/week3_day4_calibration.json")


if __name__ == "__main__":
    main()
