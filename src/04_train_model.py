"""
SupplyPrescript - Day 4: Baseline XGBoost Delay Classifier
------------------------------------------------------------
Trains an XGBoost classifier on the Day 3 train/test split to
predict Late_delivery_risk. Evaluates performance and inspects
feature importances -- also used to sanity-check for any leaky
or suspiciously dominant features (e.g. Order Status, Product Status)
flagged for review after Day 3.

Fix (post Day 3): Order Status was missed by the fixed categorical
list in 03_feature_engineering.py and reached this script as text.
Rather than patch that list again, this script auto-detects and
label-encodes any remaining object/string columns before training,
so future schema changes don't silently break XGBoost.
"""

import pandas as pd
from xgboost import XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report,
)
import joblib

DATA_DIR = "data"
MODEL_PATH = "models/xgb_baseline.pkl"


def load_splits():
    X_train = pd.read_csv(f"{DATA_DIR}/X_train.csv")
    X_test = pd.read_csv(f"{DATA_DIR}/X_test.csv")
    y_train = pd.read_csv(f"{DATA_DIR}/y_train.csv").squeeze()
    y_test = pd.read_csv(f"{DATA_DIR}/y_test.csv").squeeze()
    return X_train, X_test, y_train, y_test


def encode_leftover_text_columns(X_train: pd.DataFrame, X_test: pd.DataFrame):
    """Catch any column that's still text (e.g. Order Status) and
    label-encode it, fitting on train and applying to test."""
    text_cols = X_train.select_dtypes(include=["object", "string"]).columns.tolist()
    if text_cols:
        print(f"Auto-encoding leftover text columns: {text_cols}")
    for col in text_cols:
        le = LabelEncoder()
        # Fit on the union of train/test values so unseen test
        # categories don't break the transform.
        combined = pd.concat([X_train[col], X_test[col]], axis=0).astype(str)
        le.fit(combined)
        X_train[col] = le.transform(X_train[col].astype(str))
        X_test[col] = le.transform(X_test[col].astype(str))
    return X_train, X_test


def train_model(X_train, y_train) -> XGBClassifier:
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
    return model


def evaluate(model, X_test, y_test):
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")
    print(f"F1 Score: {f1_score(y_test, preds):.4f}")
    print(f"ROC-AUC:  {roc_auc_score(y_test, probs):.4f}")
    print()
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, preds))
    print()
    print("Classification Report:")
    print(classification_report(y_test, preds))


def feature_importances(model, X_train, top_n: int = 15):
    importances = pd.Series(
        model.feature_importances_, index=X_train.columns
    ).sort_values(ascending=False)
    print(f"Top {top_n} feature importances:")
    print(importances.head(top_n))
    return importances


def main():
    X_train, X_test, y_train, y_test = load_splits()
    print(f"Train: {X_train.shape}, Test: {X_test.shape}")
    print()

    X_train, X_test = encode_leftover_text_columns(X_train, X_test)
    print()

    model = train_model(X_train, y_train)

    print("=== Evaluation ===")
    evaluate(model, X_test, y_test)

    print("=== Feature Importances ===")
    feature_importances(model, X_train)

    joblib.dump(model, MODEL_PATH)
    print()
    print(f"Model saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
