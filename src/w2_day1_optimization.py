"""
SupplyPrescript - Week 2, Day 1: Prescriptive Optimization Setup
--------------------------------------------------------------------
Problem: Given a batch of orders flagged as high delay-risk by the
Week 1 XGBoost model, and a limited budget for shipping upgrades,
decide which orders to upgrade to minimize expected business loss
from lateness -- subject to a hard budget constraint.

This grounds the "prescriptive" step in real dataset columns rather
than invented costs:
  - Upgrade cost proxy:  Order Item Product Price (scaled)
  - Value at risk:       Order Profit Per Order (what's lost if late)
  - Risk probability:    predicted P(late) from the Day 4/5 XGBoost model

Decision variable per order: x_i in {0, 1}  (1 = upgrade shipping)

Objective: minimize expected loss
    minimize  sum( risk_i * value_at_risk_i * (1 - x_i) )
    i.e. upgrading an order (x_i=1) removes its expected loss
    (we assume upgrade reduces delay risk to ~0 for that order)

Constraint: sum( upgrade_cost_i * x_i ) <= BUDGET
"""

import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpBinary, PULP_CBC_CMD

DATA_DIR = "data"
MODEL_PATH = "models/xgb_tuned.pkl"  # falls back to xgb_baseline.pkl if not tuned yet

# Business constraint: total budget available for shipping upgrades
# on this batch of orders (illustrative -- documented assumption).
# Deliberately tight relative to full-batch upgrade cost (~$2,200 for
# 200 orders) so the optimizer has to make genuine trade-offs rather
# than trivially upgrading everyone.
BUDGET = 800.0

# Upgrade cost is modeled as a fraction of order value (proxy for the
# real-world price difference between standard and expedited shipping)
UPGRADE_COST_RATE = 0.08  # 8% of product price


def load_model():
    try:
        return joblib.load(MODEL_PATH)
    except FileNotFoundError:
        return joblib.load("models/xgb_baseline.pkl")


def encode_leftover_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """X_test.csv still has 'Order Status' as raw text -- the Day 3
    script's fixed categorical list missed it. Encode it the same way
    Day 4/5/6 did in-memory before training."""
    df = df.copy()
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in text_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
    return df


def load_batch(n_orders: int = 200) -> pd.DataFrame:
    """Simulate a daily batch: sample n_orders from the test set."""
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    X_test = encode_leftover_text_columns(X_test)
    batch = X_test.sample(n=n_orders, random_state=1).reset_index(drop=True)
    return batch


def score_batch(model, batch: pd.DataFrame) -> pd.DataFrame:
    proba = model.predict_proba(batch)[:, 1]
    batch = batch.copy()
    batch["risk_score"] = proba
    return batch


def build_optimization_inputs(batch: pd.DataFrame) -> pd.DataFrame:
    df = batch.copy()
    df["upgrade_cost"] = df["Order Item Product Price"].clip(lower=0) * UPGRADE_COST_RATE
    # Value at risk: use profit magnitude (abs, since some orders are
    # already loss-making regardless of delay)
    df["value_at_risk"] = df["Order Profit Per Order"].abs()
    return df


def solve_optimization(df: pd.DataFrame, budget: float = BUDGET):
    prob = LpProblem("ShippingUpgradeAllocation", LpMinimize)

    x = {i: LpVariable(f"upgrade_{i}", cat=LpBinary) for i in df.index}

    # Objective: minimize expected loss across the batch
    # Upgrading order i removes its expected loss (risk * value_at_risk)
    prob += lpSum(
        df.loc[i, "risk_score"] * df.loc[i, "value_at_risk"] * (1 - x[i])
        for i in df.index
    )

    # Budget constraint
    prob += lpSum(df.loc[i, "upgrade_cost"] * x[i] for i in df.index) <= budget

    prob.solve(PULP_CBC_CMD(msg=0))

    df = df.copy()
    df["upgrade_decision"] = [int(x[i].value()) for i in df.index]
    return df, prob


def main():
    model = load_model()
    batch = load_batch(n_orders=200)
    scored = score_batch(model, batch)
    opt_input = build_optimization_inputs(scored)

    result, prob = solve_optimization(opt_input, budget=BUDGET)

    n_upgraded = result["upgrade_decision"].sum()
    total_spent = (result["upgrade_cost"] * result["upgrade_decision"]).sum()
    expected_loss_before = (result["risk_score"] * result["value_at_risk"]).sum()
    expected_loss_after = (
        result["risk_score"] * result["value_at_risk"] * (1 - result["upgrade_decision"])
    ).sum()

    print(f"Batch size: {len(result)}")
    print(f"Budget: ${BUDGET:.2f}")
    print(f"Orders selected for upgrade: {n_upgraded}")
    print(f"Budget spent: ${total_spent:.2f}")
    print()
    print(f"Expected loss BEFORE optimization: ${expected_loss_before:.2f}")
    print(f"Expected loss AFTER optimization:  ${expected_loss_after:.2f}")
    print(f"Expected loss reduction: ${expected_loss_before - expected_loss_after:.2f}")
    print()

    print("Sample of prescribed decisions (top 10 by risk):")
    print(
        result.sort_values("risk_score", ascending=False)
        [["risk_score", "value_at_risk", "upgrade_cost", "upgrade_decision"]]
        .head(10)
    )

    result.to_csv("data/week2_day1_optimization_result.csv", index=False)
    print()
    print("Saved to data/week2_day1_optimization_result.csv")


if __name__ == "__main__":
    main()
