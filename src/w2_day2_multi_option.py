"""
SupplyPrescript - Week 2, Day 2: Multi-Option Prescriptive Optimization
--------------------------------------------------------------------------
Expands Day 1's binary upgrade/no-upgrade decision into 3 alternatives
per high-risk order, matching the project brief's "prescribe 3 options"
pattern -- grounded in actual dataset columns, not invented numbers.

Options per order:
  A) Upgrade shipping   -- cost = 8% of product price, removes delay
                            risk entirely for that order
  B) Compensation offer -- cost = flat $3.00 voucher (NOT price-scaled,
                            unlike upgrade), reduces expected loss by
                            60%. Decoupling the cost from price means
                            this becomes the more efficient choice for
                            higher-priced orders (where 8% upgrade cost
                            exceeds the flat $3 voucher), while upgrade
                            stays preferred for lower-priced orders.
  C) Do nothing         -- cost = 0, full expected loss remains

Decision variable per order i, per option k: x_{i,k} in {0,1}
Constraint: exactly one option chosen per order (sum_k x_{i,k} = 1)
Constraint: total cost across all chosen options <= BUDGET
Objective: minimize total expected loss across the batch
"""

import pandas as pd
import joblib
from sklearn.preprocessing import LabelEncoder
from pulp import LpProblem, LpVariable, LpMinimize, lpSum, LpBinary, PULP_CBC_CMD

DATA_DIR = "data"
MODEL_PATH = "models/xgb_tuned.pkl"

BUDGET = 800.0
UPGRADE_COST_RATE = 0.08     # Option A: 8% of product price
DISCOUNT_FLAT_COST = 3.00    # Option B: flat compensation voucher (not
                              # price-scaled -- decouples it from upgrade
                              # cost so it can be selected on its own
                              # merits for higher-price orders)
DISCOUNT_LOSS_REDUCTION = 0.60  # Option B mitigates 60% of expected loss


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


def load_batch(n_orders: int = 200) -> pd.DataFrame:
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    X_test = encode_leftover_text_columns(X_test)
    return X_test.sample(n=n_orders, random_state=1).reset_index(drop=True)


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


def solve_multi_option(df: pd.DataFrame, budget: float = BUDGET):
    prob = LpProblem("MultiOptionPrescription", LpMinimize)

    options = ["upgrade", "discount", "nothing"]
    x = {
        (i, opt): LpVariable(f"x_{i}_{opt}", cat=LpBinary)
        for i in df.index for opt in options
    }

    # Exactly one option per order
    for i in df.index:
        prob += lpSum(x[(i, opt)] for opt in options) == 1

    # Budget constraint: sum of costs across chosen options
    prob += lpSum(
        x[(i, "upgrade")] * df.loc[i, "upgrade_cost"]
        + x[(i, "discount")] * df.loc[i, "discount_cost"]
        + x[(i, "nothing")] * 0
        for i in df.index
    ) <= budget

    # Objective: minimize total expected loss
    #   upgrade -> loss = 0
    #   discount -> loss = base_loss * (1 - DISCOUNT_LOSS_REDUCTION)
    #   nothing -> loss = base_loss
    prob += lpSum(
        x[(i, "upgrade")] * 0
        + x[(i, "discount")] * df.loc[i, "base_expected_loss"] * (1 - DISCOUNT_LOSS_REDUCTION)
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


def summarize(df: pd.DataFrame):
    counts = df["decision"].value_counts()
    print("Decision breakdown:")
    print(counts)
    print()

    cost = (
        (df["decision"] == "upgrade") * df["upgrade_cost"]
        + (df["decision"] == "discount") * df["discount_cost"]
    ).sum()

    loss_after = (
        (df["decision"] == "upgrade") * 0
        + (df["decision"] == "discount") * df["base_expected_loss"] * (1 - DISCOUNT_LOSS_REDUCTION)
        + (df["decision"] == "nothing") * df["base_expected_loss"]
    ).sum()

    loss_before = df["base_expected_loss"].sum()

    print(f"Total cost: ${cost:.2f} / ${BUDGET:.2f} budget")
    print(f"Expected loss BEFORE: ${loss_before:.2f}")
    print(f"Expected loss AFTER:  ${loss_after:.2f}")
    print(f"Reduction: ${loss_before - loss_after:.2f} ({(loss_before-loss_after)/loss_before*100:.1f}%)")


def main():
    model = load_model()
    batch = load_batch(n_orders=200)
    scored = score_batch(model, batch)
    opt_input = build_options(scored)

    result = solve_multi_option(opt_input, budget=BUDGET)

    summarize(result)
    print()
    print("Sample of prescribed decisions (top 10 by risk):")
    print(
        result.sort_values("risk_score", ascending=False)
        [["risk_score", "value_at_risk", "upgrade_cost", "discount_cost", "decision"]]
        .head(10)
    )

    result.to_csv("data/week2_day2_multi_option_result.csv", index=False)
    print()
    print("Saved to data/week2_day2_multi_option_result.csv")


if __name__ == "__main__":
    main()
