"""
SupplyPrescript - Day 5: Shipping Mode Investigation
------------------------------------------------------
Day 4's baseline (Model A) showed Shipping Mode dominating feature
importance at ~70%, with every other feature flat around 1%. This
matches the Day 2 EDA finding that Shipping Mode maps almost 1:1 to
a fixed scheduled-day value, making it behave more like an encoded
proxy for the label than a genuine multi-factor predictor.

This script trains Model B (same features, minus Shipping Mode) and
compares it against Model A so the report can present this as a
deliberate investigation rather than an unexplained result.
"""

import pandas as pd
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import joblib

DATA_DIR = "data"
MODEL_A_PATH = "models/xgb_baseline.pkl"
MODEL_B_PATH = "models/xgb_no_shipping_mode.pkl"


def load_splits():
    X_train = pd.read_csv(f"{DATA_DIR}/X_train.csv")
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    y_train = pd.read_csv(f"{DATA_DIR}/y_train.csv").squeeze()
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()
    return X_train, X_test, y_train, y_test


def encode_leftover_text_columns(X_train: pd.DataFrame, X_test: pd.DataFrame):
    text_cols = X_train.select_dtypes(include=["object", "string"]).columns.tolist()
    for col in text_cols:
        le = LabelEncoder()
        combined = pd.concat([X_train[col], X_test[col]], axis=0).astype(str)
        le.fit(combined)
        X_train[col] = le.transform(X_train[col].astype(str))
        X_test[col] = le.transform(X_test[col].astype(str))
    return X_train, X_test


def train_and_eval(X_train, X_test, y_train, y_test, model_path: str, label: str):
    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds)
    auc = roc_auc_score(y_test, probs)

    print(f"=== {label} ===")
    print(f"Accuracy: {acc:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print(f"ROC-AUC:  {auc:.4f}")

    importances = pd.Series(
        model.feature_importances_, index=X_train.columns
    ).sort_values(ascending=False)
    print(f"Top 10 feature importances:")
    print(importances.head(10))
    print()

    joblib.dump(model, model_path)

    return {"accuracy": acc, "f1": f1, "roc_auc": auc}


def main():
    X_train, X_test, y_train, y_test = load_splits()
    X_train, X_test = encode_leftover_text_columns(X_train, X_test)

    # --- Model A: with Shipping Mode (Day 4 baseline, retrained here
    # for a clean side-by-side comparison in one run) ---
    results_a = train_and_eval(
        X_train, X_test, y_train, y_test,
        MODEL_A_PATH, "Model A: WITH Shipping Mode"
    )

    # --- Model B: without Shipping Mode ---
    X_train_b = X_train.drop(columns=["Shipping Mode"])
    X_test_b = X_test.drop(columns=["Shipping Mode"])
    results_b = train_and_eval(
        X_train_b, X_test_b, y_train, y_test,
        MODEL_B_PATH, "Model B: WITHOUT Shipping Mode"
    )

    print("=== Comparison ===")
    comparison = pd.DataFrame([results_a, results_b], index=["Model A (with)", "Model B (without)"])
    print(comparison)


if __name__ == "__main__":
    main()
