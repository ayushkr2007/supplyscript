"""
SupplyPrescript - Week 3, Day 1: Predicted vs. Actual Evaluation
--------------------------------------------------------------------------
Closes the loop by checking each executed decision's predicted risk
against the REAL outcome for that order, using the ground-truth
Late_delivery_risk label from the held-out test set.

IMPORTANT HONESTY NOTE: this is a retrospective evaluation against
historical ground truth, not a live causal experiment. Because the
batch orders come from the test set (already-delivered, historical
orders), we cannot know whether upgrading shipping would have
actually prevented a real delay -- we can't re-run history with a
different shipping mode. What we CAN honestly evaluate is whether the
model's risk predictions that drove each decision were accurate. That
is what this script does: it checks prediction correctness, not
causal intervention effectiveness. This distinction matters and
should be stated plainly in the project write-up.

The money spent (actual_cost) IS certain -- that part is simply
copied from the decision's recorded cost, since it reflects real
budget committed regardless of outcome.
"""

import sqlite3
import pandas as pd

DATA_DIR = "data"
DB_PATH = "data/supplyprescript.db"


def load_true_labels(n_orders: int = 200, seed: int = 1) -> pd.Series:
    """Reproduce the exact same sample used by prescribe_batch() so
    order_id (0..n_orders-1, positional after sampling) aligns with
    the correct ground-truth label."""
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()

    sampled_idx = X_test.sample(n=n_orders, random_state=seed).index
    y_sampled = y_test.loc[sampled_idx].reset_index(drop=True)
    return y_sampled


def evaluate_decisions(n_orders: int = 200, seed: int = 1):
    true_labels = load_true_labels(n_orders=n_orders, seed=seed)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    decisions = conn.execute("SELECT * FROM decisions").fetchall()

    results = []
    for d in decisions:
        order_id = d["order_id"]
        if order_id >= len(true_labels):
            continue  # order_id from a different batch config; skip safely

        true_label = int(true_labels.iloc[order_id])
        actual_outcome = "late" if true_label == 1 else "on_time"
        predicted_late = d["risk_score"] > 0.5
        prediction_correct = predicted_late == (true_label == 1)

        conn.execute(
            "UPDATE decisions SET actual_outcome = ?, actual_cost = ? WHERE id = ?",
            (actual_outcome, d["cost"], d["id"]),
        )

        results.append({
            "id": d["id"],
            "order_id": order_id,
            "decision": d["decision"],
            "risk_score": d["risk_score"],
            "predicted_late": predicted_late,
            "actual_outcome": actual_outcome,
            "prediction_correct": prediction_correct,
        })

    conn.commit()
    conn.close()
    return results


def summarize(results: list):
    total = len(results)
    correct = sum(1 for r in results if r["prediction_correct"])
    truly_late = sum(1 for r in results if r["actual_outcome"] == "late")

    print(f"Evaluated {total} executed decisions")
    print(f"Prediction accuracy on these orders: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"Of these, {truly_late} orders ({truly_late/total*100:.1f}%) were actually late historically")
    print()

    by_decision = {}
    for r in results:
        by_decision.setdefault(r["decision"], []).append(r)

    print("Breakdown by decision type:")
    for decision, group in by_decision.items():
        n = len(group)
        n_correct = sum(1 for r in group if r["prediction_correct"])
        n_late = sum(1 for r in group if r["actual_outcome"] == "late")
        print(f"  {decision}: {n} decisions, {n_correct}/{n} predictions correct, {n_late} truly late")


def main():
    results = evaluate_decisions()
    if not results:
        print("No executed decisions found (or none matched this batch config).")
        print("Execute some decisions via the dashboard first, then re-run this.")
        return

    summarize(results)
    print()
    print("Database updated: actual_outcome and actual_cost filled in for all matched decisions.")


if __name__ == "__main__":
    main()
