"""
SupplyPrescript - Week 3, Day 2: Full-Batch Prescription Evaluation
--------------------------------------------------------------------------
Day 1 evaluated only the 5 orders manually executed via the dashboard --
too small a sample to say much. This script evaluates the OPTIMIZER'S
full set of prescriptions (all 200 orders in the batch) against real
ground-truth outcomes, answering a more useful question:

    "If we had acted on every prescription the optimizer made, how
    much of the claimed loss reduction is actually validated by real
    historical outcomes -- and where did the optimizer spend money on
    orders that were never actually going to be late?"

Same honesty caveat as Day 1: this is a retrospective evaluation
against historical ground truth, not a live causal experiment. We
can't know if an upgrade would have *actually* prevented a real
delay -- only whether the model's risk prediction that drove the
decision was correct.

Key metrics:
- Precision: of orders the optimizer spent money on (upgrade/discount),
  what fraction were actually late? (money well-targeted)
- Recall: of orders that were actually late, what fraction did the
  optimizer flag for action? (coverage of real risk)
- Wasted spend: money spent on orders that were NOT actually late
  (false positives -- a cost of imperfect prediction)
- Missed value: expected value at risk among truly-late orders the
  optimizer left untouched (false negatives)
"""

import json
import pandas as pd

DATA_DIR = "data"
PRESCRIPTIONS_PATH = f"{DATA_DIR}/prescriptions.json"


def load_true_labels(n_orders: int = 200, seed: int = 1) -> pd.Series:
    """Reproduce the exact sample used by prescribe_batch() so
    order_id aligns with the correct ground-truth label."""
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()

    sampled_idx = X_test.sample(n=n_orders, random_state=seed).index
    y_sampled = y_test.loc[sampled_idx].reset_index(drop=True)
    return y_sampled


def load_prescriptions() -> dict:
    with open(PRESCRIPTIONS_PATH) as f:
        return json.load(f)


def evaluate_full_batch():
    prescriptions = load_prescriptions()
    orders = prescriptions["orders"]
    n_orders = len(orders)
    true_labels = load_true_labels(n_orders=n_orders)

    acted_on = [o for o in orders if o["decision"] in ("upgrade", "discount")]
    skipped = [o for o in orders if o["decision"] == "nothing"]

    # Precision: of orders we spent money on, how many were truly late?
    acted_true_late = sum(1 for o in acted_on if true_labels.iloc[o["order_id"]] == 1)
    precision = acted_true_late / len(acted_on) if acted_on else 0

    # Recall: of truly-late orders, how many did we act on?
    total_truly_late = sum(1 for i in range(n_orders) if true_labels.iloc[i] == 1)
    recall = acted_true_late / total_truly_late if total_truly_late else 0

    # Wasted spend: cost spent on orders that were NOT actually late
    wasted_spend = sum(
        o["cost"] for o in acted_on if true_labels.iloc[o["order_id"]] == 0
    )
    total_spend = sum(o["cost"] for o in acted_on)

    # Missed value: expected value at risk among truly-late orders we skipped
    missed_value = sum(
        o["value_at_risk"] for o in skipped if true_labels.iloc[o["order_id"]] == 1
    )

    return {
        "n_orders": n_orders,
        "n_acted_on": len(acted_on),
        "n_skipped": len(skipped),
        "total_truly_late": total_truly_late,
        "acted_true_late": acted_true_late,
        "precision": precision,
        "recall": recall,
        "total_spend": round(total_spend, 2),
        "wasted_spend": round(wasted_spend, 2),
        "wasted_spend_pct": round(wasted_spend / total_spend * 100, 1) if total_spend else 0,
        "missed_value": round(missed_value, 2),
    }


def main():
    stats = evaluate_full_batch()

    print(f"Full batch: {stats['n_orders']} orders")
    print(f"  Truly late (ground truth): {stats['total_truly_late']} ({stats['total_truly_late']/stats['n_orders']*100:.1f}%)")
    print()
    print(f"Optimizer acted on: {stats['n_acted_on']} orders ({stats['n_acted_on']/stats['n_orders']*100:.1f}%)")
    print(f"Optimizer skipped:  {stats['n_skipped']} orders")
    print()
    print(f"Precision (of $ spent, % truly late): {stats['precision']*100:.1f}%")
    print(f"Recall (of truly-late orders, % covered): {stats['recall']*100:.1f}%")
    print()
    print(f"Total spend: ${stats['total_spend']}")
    print(f"Wasted spend (on orders that were NOT truly late): ${stats['wasted_spend']} ({stats['wasted_spend_pct']}%)")
    print(f"Missed value (truly-late orders left untouched): ${stats['missed_value']}")
    print()
    print("NOTE: this evaluates prediction targeting against historical")
    print("ground truth, not causal intervention effectiveness -- see")
    print("module docstring for the full caveat.")

    with open(f"{DATA_DIR}/week3_day2_full_batch_eval.json", "w") as f:
        json.dump(stats, f, indent=2)
    print()
    print(f"Saved to {DATA_DIR}/week3_day2_full_batch_eval.json")


if __name__ == "__main__":
    main()
