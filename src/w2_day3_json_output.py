"""
SupplyPrescript - Week 2, Day 3: JSON Output Layer
--------------------------------------------------------------------------
Wraps Day 2's multi-option optimizer into a single reusable function
(`prescribe_batch`) that returns a clean, JSON-serializable structure
per order -- ready for the React dashboard (or a future FastAPI
endpoint in Week 3) to consume directly.

NOTE (mid-review fix): total_cost in the summary is computed from the
*unrounded* per-order costs, not by summing the already-rounded
per-order display values. Summing rounded numbers can drift a few
cents above budget purely from rounding, even though the LP itself
always respects the budget constraint on the true unrounded costs.
This was caught by the mid-review budget audit.
"""

import json
import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpBinary, PULP_CBC_CMD

DATA_DIR = "data"
MODEL_PATH = "models/xgb_tuned.pkl"

BUDGET = 800.0
UPGRADE_COST_RATE = 0.08
DISCOUNT_FLAT_COST = 3.00
DISCOUNT_LOSS_REDUCTION = 0.60


def load_model():
    try:
        return joblib.load(MODEL_PATH)
    except FileNotFoundError:
        return joblib.load("models/xgb_baseline.pkl")


def encode_leftover_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in text_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
    return df


def load_batch(n_orders: int = 200, seed: int = 1) -> pd.DataFrame:
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    X_test = encode_leftover_text_columns(X_test)
    return X_test.sample(n=n_orders, random_state=seed).reset_index(drop=True)


def score_batch(model, batch: pd.DataFrame) -> pd.DataFrame:
    proba = model.predict_proba(batch)[:, 1]
    batch = batch.copy()
    batch["risk_score"] = proba
    return batch


def build_options(batch: pd.DataFrame) -> pd.DataFrame:
    df = batch.copy()
    df["upgrade_cost"] = df["Order Item Product Price"].clip(lower=0) * UPGRADE_COST_RATE
    df["discount_cost"] = DISCOUNT_FLAT_COST
    df["value_at_risk"] = df["Order Profit Per Order"].abs()
    df["base_expected_loss"] = df["risk_score"] * df["value_at_risk"]
    return df


def solve_multi_option(df: pd.DataFrame, budget: float = BUDGET) -> pd.DataFrame:
    prob = LpProblem("MultiOptionPrescription", LpMinimize)
    options = ["upgrade", "discount", "nothing"]
    x = {
        (i, opt): LpVariable(f"x_{i}_{opt}", cat=LpBinary)
        for i in df.index for opt in options
    }

    for i in df.index:
        prob += lpSum(x[(i, opt)] for opt in options) == 1

    prob += lpSum(
        x[(i, "upgrade")] * df.loc[i, "upgrade_cost"]
        + x[(i, "discount")] * df.loc[i, "discount_cost"]
        for i in df.index
    ) <= budget

    prob += lpSum(
        x[(i, "discount")] * df.loc[i, "base_expected_loss"] * (1 - DISCOUNT_LOSS_REDUCTION)
        + x[(i, "nothing")] * df.loc[i, "base_expected_loss"]
        for i in df.index
    )

    prob.solve(PULP_CBC_CMD(msg=0))

    decisions = []
    for i in df.index:
        chosen = next(opt for opt in options if x[(i, opt)].value() == 1)
        decisions.append(chosen)
    df = df.copy()
    df["decision"] = decisions
    return df


def to_json_records(df: pd.DataFrame) -> list:
    records = []
    for i, row in df.iterrows():
        base_loss = row["base_expected_loss"]
        options = {
            "upgrade": {
                "cost": round(row["upgrade_cost"], 2),
                "expected_loss_after": 0.0,
            },
            "discount": {
                "cost": round(row["discount_cost"], 2),
                "expected_loss_after": round(base_loss * (1 - DISCOUNT_LOSS_REDUCTION), 2),
            },
            "nothing": {
                "cost": 0.0,
                "expected_loss_after": round(base_loss, 2),
            },
        }
        chosen = row["decision"]
        raw_cost = (
            row["upgrade_cost"] if chosen == "upgrade"
            else row["discount_cost"] if chosen == "discount"
            else 0.0
        )
        records.append({
            "order_id": int(i),
            "risk_score": round(float(row["risk_score"]), 4),
            "value_at_risk": round(float(row["value_at_risk"]), 2),
            "decision": chosen,
            "cost": options[chosen]["cost"],
            "_raw_cost": float(raw_cost),
            "expected_loss_before": round(float(base_loss), 2),
            "expected_loss_after": options[chosen]["expected_loss_after"],
            "options": options,
        })
    return records


def prescribe_batch(n_orders: int = 200, budget: float = BUDGET, seed: int = 1) -> dict:
    model = load_model()
    batch = load_batch(n_orders=n_orders, seed=seed)
    scored = score_batch(model, batch)
    opt_input = build_options(scored)
    result = solve_multi_option(opt_input, budget=budget)

    records = to_json_records(result)

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


def main():
    result = prescribe_batch()

    print("=== Summary ===")
    print(json.dumps(result["summary"], indent=2))
    print()
    print("=== Sample order record ===")
    print(json.dumps(result["orders"][0], indent=2))

    with open("data/prescriptions.json", "w") as f:
        json.dump(result, f, indent=2)
    print()
    print("Saved full result to data/prescriptions.json")


if __name__ == "__main__":
    main()
