"""
SupplyPrescript - Day 3: Feature Engineering
------------------------------------------------------
Builds on Day 2's cleaned dataset. Prepares features for the
XGBoost delay classifier:
  - Drops leakage columns (anything that encodes the actual outcome)
  - Resolves Shipping Mode <-> Days for shipment (scheduled) redundancy
    by keeping Shipping Mode only (more interpretable, same signal)
  - Encodes categorical features
  - Extracts date-based features from order date
  - Produces a train/test split ready for Day 4 modeling
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

DATA_PATH = "data/cleaned_day2.csv"

# Columns that leak the outcome -- these directly encode or are
# computed from whether/how late the order was delivered.
LEAKAGE_COLS = [
    "Days for shipping (real)",
    "Delivery Status",
    "Late_delivery_risk",  # target -- excluded from X separately
]

# Redundant with Shipping Mode (near-1:1 mapping, confirmed Day 2 EDA)
REDUNDANT_COLS = ["Days for shipment (scheduled)"]

# High-cardinality / identifier columns not useful as direct features
ID_COLS = [
    "Order Id", "Order Item Id", "Order Item Cardprod Id",
    "Product Card Id", "Product Name", "Customer Id", "Customer Email",
    "Customer Fname", "Customer Lname", "Customer Password",
    "Customer Street", "Customer Zipcode", "Order Zipcode",
    "Order Customer Id", "Product Image",
]

CATEGORICAL_COLS = [
    "Shipping Mode", "Order Region", "Order Country", "Order State",
    "Order City", "Category Name", "Department Name", "Market",
    "Customer Segment", "Customer Country", "Customer State",
    "Customer City", "Type",
]

DATE_COL = "order date (DateOrders)"


def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path, encoding="ISO-8859-1")


def extract_date_features(df: pd.DataFrame) -> pd.DataFrame:
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df["order_month"] = df[DATE_COL].dt.month
    df["order_dayofweek"] = df[DATE_COL].dt.dayofweek
    df["order_quarter"] = df[DATE_COL].dt.quarter
    df["order_is_weekend"] = df["order_dayofweek"].isin([5, 6]).astype(int)
    return df


def encode_categoricals(df: pd.DataFrame, cols: list) -> tuple[pd.DataFrame, dict]:
    encoders = {}
    for col in cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            encoders[col] = le
    return df, encoders


def build_feature_set(df: pd.DataFrame) -> pd.DataFrame:
    df = extract_date_features(df)

    drop_cols = [c for c in (LEAKAGE_COLS + REDUNDANT_COLS + ID_COLS)
                 if c in df.columns and c != "Late_delivery_risk"]
    df = df.drop(columns=drop_cols)

    # Drop any remaining datetime columns raw form (kept only engineered parts)
    remaining_date_cols = [c for c in df.columns if "date" in c.lower()]
    df = df.drop(columns=remaining_date_cols, errors="ignore")

    df, encoders = encode_categoricals(df, CATEGORICAL_COLS)

    return df


def main():
    df = load_data()
    print(f"Input shape: {df.shape}")

    df = build_feature_set(df)
    print(f"Feature-engineered shape: {df.shape}")
    print()
    print("Remaining columns:")
    for c in df.columns:
        print(" -", c)

    y = df["Late_delivery_risk"]
    X = df.drop(columns=["Late_delivery_risk"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print()
    print(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")
    print(f"Train target balance:\n{y_train.value_counts(normalize=True)}")

    # Save for Day 4 modeling
    X_train.to_csv("data/X_train.csv", index=False)
    X_test.to_csv("data/X_test.csv", index=False)
    y_train.to_csv("data/y_train.csv", index=False)
    y_test.to_csv("data/y_test.csv", index=False)
    print()
    print("Saved train/test splits to data/")


if __name__ == "__main__":
    main()
