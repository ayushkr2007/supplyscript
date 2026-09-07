"""
SupplyPrescript - Day 6: Hyperparameter Tuning
------------------------------------------------------------
Tunes the Model A (WITH Shipping Mode) XGBoost classifier confirmed
as primary in Day 5. Uses RandomizedSearchCV with stratified CV
folds to search a reasonable hyperparameter space, then compares
the tuned model against the Day 4/5 baseline.
"""

import pandas as pd
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
import joblib

DATA_DIR = "data"
BASELINE_METRICS = {"accuracy": 0.7345, "f1": 0.7356, "roc_auc": 0.8259}


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


def main():
    X_train, X_test, y_train, y_test = load_splits()
    X_train, X_test = encode_leftover_text_columns(X_train, X_test)

    param_dist = {
        "n_estimators": [150, 200, 300, 400],
        "max_depth": [4, 5, 6, 7, 8],
        "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.15],
        "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
        "min_child_weight": [1, 3, 5, 7],
        "gamma": [0, 0.1, 0.2, 0.3],
    }

    base_model = XGBClassifier(
        eval_metric="logloss",
        random_state=42,
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    search = RandomizedSearchCV(
        estimator=base_model,
        param_distributions=param_dist,
        n_iter=30,
        scoring="roc_auc",
        cv=cv,
        verbose=2,
        random_state=42,
        n_jobs=-1,
    )

    print("Starting hyperparameter search (this may take several minutes)...")
    search.fit(X_train, y_train)

    print()
    print("Best params found:")
    print(search.best_params_)
    print(f"Best CV ROC-AUC: {search.best_score_:.4f}")

    best_model = search.best_estimator_

    preds = best_model.predict(X_test)
    proba = best_model.predict_proba(X_test)[:, 1]

    tuned_metrics = {
        "accuracy": accuracy_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        "roc_auc": roc_auc_score(y_test, proba),
    }

    print()
    print("=== Tuned model performance on test set ===")
    for k, v in tuned_metrics.items():
        print(f"{k}: {v:.4f}")

    print()
    print("=== Comparison: baseline (Day 4/5) vs tuned ===")
    comparison = pd.DataFrame(
        [BASELINE_METRICS, tuned_metrics], index=["Baseline", "Tuned"]
    )
    print(comparison)

    joblib.dump(best_model, "models/xgb_tuned.pkl")
    print()
    print("Tuned model saved to models/xgb_tuned.pkl")


if __name__ == "__main__":
    main()
